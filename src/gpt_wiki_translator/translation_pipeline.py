from __future__ import annotations
from pathlib import Path
from typing import List
from .config import get_settings
from .logging_utils import get_logger
from .mediawiki_client import MediaWikiClient
from .openai_client import OpenAIClient
from .wikitext_parser import segment_wikitext, merge_translated, count_braces, restore_protected_template_params
from .namespace_mapping import translate_namespace_prefix
from .chunking import create_chunks, get_chunk_stats
import csv
from tqdm import tqdm
import json
from datetime import datetime, timezone

logger = get_logger()

class TranslationPipeline:
    def __init__(self, source_endpoint: str, target_endpoint: str, source_lang: str, target_lang: str, dry_run: bool = False, force: bool = False, verify_ssl: bool = True):
        self.settings = get_settings()
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.dry_run = dry_run
        self.force = force
        self.verify_ssl = verify_ssl
        self.source_mw = MediaWikiClient(source_endpoint, verify_ssl=verify_ssl)
        self.target_mw = MediaWikiClient(target_endpoint, verify_ssl=verify_ssl)
        self.ai = OpenAIClient()
        self.log_path = Path(self.settings.log_csv_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            with self.log_path.open('w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['source_page','target_page','source_lang','target_lang','status','date_iso','notes'])

    def _append_log(self, row: List[str]):
        with self.log_path.open('a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)

    def _translate_title(self, title: str) -> str:
        """Translate page title from source language to target language.
        Handles namespace prefixes separately."""
        # Split namespace and actual title
        if ':' in title:
            parts = title.split(':', 1)
            namespace = parts[0]
            page_name = parts[1]
        else:
            namespace = None
            page_name = title
        
        # Translate the namespace prefix (Catégorie -> Category, etc.)
        if namespace:
            translated_namespace = translate_namespace_prefix(namespace + ':', self.source_lang, self.target_lang).rstrip(':')
        else:
            translated_namespace = None
        
        # Translate the page name itself using OpenAI
        try:
            prompt = f"Translate this page title from {self.source_lang} to {self.target_lang}. Return ONLY the translated title, nothing else: {page_name}"
            translated_page_name = self.ai.translate_chunk(prompt, self.source_lang, self.target_lang).strip()
            # Remove quotes or extra formatting if AI added them
            translated_page_name = translated_page_name.strip('"\'')
        except Exception as e:
            logger.warning('Failed to translate title "%s": %s. Using original.', page_name, e)
            translated_page_name = page_name
        
        # Reconstruct the full title
        if translated_namespace:
            return f"{translated_namespace}:{translated_page_name}"
        else:
            return translated_page_name

    def process_pages(self, titles: List[str]):
        for title in tqdm(titles, desc='Pages'):
            self.process_single_page(title.strip())

    def process_single_page(self, title: str):
        if not title or title.startswith('#'):
            return
        langlinks = self.source_mw.get_langlinks(title)
        if self.target_lang in langlinks and not self.force:
            logger.info('Skip %s (already translated -> %s)', title, langlinks[self.target_lang])
            date_iso = datetime.now(timezone.utc).isoformat()
            self._append_log([title, langlinks[self.target_lang], self.source_lang, self.target_lang, 'skipped', date_iso, 'already translated and present in the interwiki links'])
            return
        elif self.target_lang in langlinks and self.force:
            logger.info('Force mode: retranslating %s (existing: %s)', title, langlinks[self.target_lang])
        
        # Translate title early to check if target exists (avoid unnecessary API calls)
        target_title = self._translate_title(title)
        target_exists = self.target_mw.page_exists(target_title)
        
        # If target exists and --force not specified, only add interwiki link (no translation needed)
        if target_exists and not self.force:
            logger.info('Target page %s already exists. Only adding interwiki link to source page.', target_title)
            if not self.dry_run:
                target_interwiki = f"[[{self.target_lang}:{target_title}]]"
                self.source_mw.append_interwiki_link(title, target_interwiki)
            date_iso = datetime.now(timezone.utc).isoformat()
            self._append_log([title, target_title, self.source_lang, self.target_lang, 'linked', date_iso, 'target exists - adding interwiki on the source page only'])
            logger.info('Linked %s -> %s (target exists)', title, target_title)
            return
        
        wikitext = self.source_mw.fetch_page_wikitext(title)
        if wikitext is None:
            logger.warning('No wikitext for %s', title)
            date_iso = datetime.now(timezone.utc).isoformat()
            self._append_log([title, '', self.source_lang, self.target_lang, 'error', date_iso, 'missing wikitext'])
            return
        
        # Use intelligent chunking by sections
        chunks = create_chunks(wikitext, max_tokens=7000)
        stats = get_chunk_stats(chunks)
        logger.info('Page %s: %d chunks, avg %d tokens/chunk', title, stats['count'], stats['avg_tokens'])
        
        # Translate each chunk
        translated_chunks: List[str] = []
        for i, chunk in enumerate(tqdm(chunks, desc=f'Translating {title}', leave=False)):
            translated = self.ai.translate_chunk(chunk, self.source_lang, self.target_lang)
            translated_chunks.append(translated)
        # Reconstruct full translated wikitext
        new_wikitext = '\n\n'.join(translated_chunks)
        # Restore protected template parameter values (Glyph, Icone, etc.)
        new_wikitext = restore_protected_template_params(wikitext, new_wikitext)
        # Validation simple locale
        ob_open, ob_close = count_braces(wikitext)
        nb_open, nb_close = count_braces(new_wikitext)
        if ob_open != nb_open or ob_close != nb_close:
            logger.warning('Brace count mismatch for %s', title)
        validation_raw = self.ai.validate_translation(wikitext, new_wikitext)
        try:
            validation = json.loads(validation_raw)
        except json.JSONDecodeError:
            validation = {'issues': ['invalid JSON from validator']}
        
        # Publish translated page (target_title already computed earlier)
        if not self.dry_run:
            # Create/update target page with interwiki link back to source
            source_interwiki = f"[[{self.source_lang}:{title}]]"
            new_wikitext_with_interwiki = new_wikitext + f"\n{source_interwiki}\n"
            
            publish_resp = self.target_mw.create_or_update_page(target_title, new_wikitext_with_interwiki)
            
            # Also add interwiki link in source page pointing to target
            target_interwiki = f"[[{self.target_lang}:{target_title}]]"
            self.source_mw.append_interwiki_link(title, target_interwiki)
        else:
            publish_resp = {'dry_run': True}
        
        # Add timestamp to log
        date_iso = datetime.now(timezone.utc).isoformat()
        self._append_log([title, target_title, self.source_lang, self.target_lang, 'translated', date_iso, ';'.join(validation.get('issues', []))])
        logger.info('Translated %s -> %s (%s)', title, target_title, 'dry-run' if self.dry_run else 'published')
