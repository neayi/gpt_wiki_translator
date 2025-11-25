from __future__ import annotations
from pathlib import Path
from typing import List
from .config import get_settings
from .logging_utils import get_logger
from .mediawiki_client import MediaWikiClient
from .openai_client import OpenAIClient
from .wikitext_parser import (
    segment_wikitext,
    merge_translated,
    count_braces,
    restore_protected_template_params,
    extract_json_template_params,
    mask_templates_for_translation,
    restore_masked_templates,
)
from .namespace_mapping import translate_namespace_prefix
from .chunking import create_chunks, get_chunk_stats
import csv
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
        # cache for other language clients
        self._other_clients: dict[str, MediaWikiClient] = {}

    def _derive_endpoint_for_lang(self, base_endpoint: str, lang: str) -> str:
        """Derive an endpoint for another language by replacing first subdomain segment."""
        from urllib.parse import urlparse, urlunparse
        p = urlparse(base_endpoint)
        parts = p.netloc.split('.')
        if parts:
            parts[0] = lang
        netloc = '.'.join(parts)
        return urlunparse((p.scheme, netloc, p.path, '', '', ''))

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
        for title in titles:
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
        
        # Determine target title without creating duplicates:
        # If an interlanguage link already exists on the source, reuse that exact target title
        # even in --force mode to avoid creating a duplicate target page with a different title.
        if self.target_lang in langlinks:
            target_title = langlinks[self.target_lang]
        else:
            # Otherwise, translate the title and check if such a page exists on target
            target_title = self._translate_title(title)

        target_exists = self.target_mw.page_exists(target_title)
        
        # If target exists and --force not specified, only add interwiki link (no translation needed)
        if target_exists and not self.force:
            logger.info('Target page %s already exists. Only adding interwiki link to source page.', target_title)
            if not self.dry_run:
                target_interwiki = f"[[{self.target_lang}:{target_title}]]"
                self.source_mw.add_or_update_interwiki_link(title, target_interwiki)
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

        # Detect JSON subpage references in templates
        json_refs = extract_json_template_params(wikitext)
        json_replacements = {}
        json_placeholder_mapping = {}
        if json_refs:
            logger.info('Found %d JSON template references', len(json_refs))
            for idx, raw in enumerate(json_refs):
                # Expect pattern Base/Subpage.json
                if not raw.lower().endswith('.json') or '/' not in raw:
                    continue
                base, subfile = raw.rsplit('/', 1)
                subname = subfile[:-5]  # remove .json
                # Translate subpage name using AI (keep .json extension)
                try:
                    translated_subname = self.ai.translate_chunk(
                        f"Translate this short name for a JSON subpage from {self.source_lang} to {self.target_lang}. Return ONLY the translated name: {subname}",
                        self.source_lang,
                        self.target_lang
                    ).strip().strip('"\'')
                except Exception:
                    translated_subname = subname
                # Build target JSON path: target_title/translated_subname.json
                target_json_path = f"{target_title}/{translated_subname}.json"
                # Fetch original JSON content
                orig_json_text = self.source_mw.fetch_page_wikitext(raw) or ''
                translated_json_text = orig_json_text
                # Attempt structured translation if JSON
                import json as pyjson
                try:
                    data_obj = pyjson.loads(orig_json_text)
                    # Ask model to translate JSON values preserving structure
                    json_translation_prompt = (
                        f"Translate the human-readable string VALUES inside this JSON from {self.source_lang} to {self.target_lang}. "
                        "Do not change keys, numbers, or structure. Return valid JSON only.\n\n" + orig_json_text
                    )
                    translated_json_raw = self.ai.translate_chunk(json_translation_prompt, self.source_lang, self.target_lang)
                    data_trans = pyjson.loads(translated_json_raw)
                    translated_json_text = pyjson.dumps(data_trans, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.warning('JSON translation failed or not JSON for %s: %s (keeping original)', raw, e)
                # Create/update JSON page on target wiki using the exact path
                if not self.dry_run:
                    self.target_mw.create_or_update_json_page(target_json_path, translated_json_text)
                # Store replacement: original path -> target path (same path used for page creation)
                json_replacements[raw] = target_json_path
                # Create placeholder to prevent AI from translating this path
                json_placeholder = f"⟪JSON_PATH_{idx}⟫"
                json_placeholder_mapping[json_placeholder] = target_json_path
                logger.info('JSON translation: %s -> %s', raw, target_json_path)
        
        # Replace JSON paths in wikitext with placeholders before translation
        wikitext_with_placeholders = wikitext
        for original, placeholder in zip(json_refs, [f"⟪JSON_PATH_{i}⟫" for i in range(len(json_refs))]):
            if original in json_replacements:
                wikitext_with_placeholders = wikitext_with_placeholders.replace(original, placeholder)
        
        # Mask template names and parameter keys to prevent their translation
        masked_wikitext, template_mapping = mask_templates_for_translation(wikitext_with_placeholders)

        # Use intelligent chunking by sections on masked wikitext
        chunks = create_chunks(masked_wikitext, max_tokens=7000)
        # stats = get_chunk_stats(chunks)
        logger.info('Translating page: %s', title)
        
        # Translate each chunk
        translated_chunks: List[str] = []
        for i, chunk in enumerate(chunks):
            translated = self.ai.translate_chunk(chunk, self.source_lang, self.target_lang)
            translated_chunks.append(translated)
        # Reconstruct full translated wikitext
        new_wikitext_masked = '\n\n'.join(translated_chunks)
        # Restore template names and keys
        new_wikitext = restore_masked_templates(new_wikitext_masked, template_mapping)
        # Restore protected template parameter values (Glyph, Icone, etc.)
        new_wikitext = restore_protected_template_params(wikitext, new_wikitext)
        # Replace JSON placeholders with translated paths
        for placeholder, target_path in json_placeholder_mapping.items():
            new_wikitext = new_wikitext.replace(placeholder, target_path)
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
            # Build interwiki markers: source + any existing other languages
            other_markers = []
            for lang, other_page_title in langlinks.items():
                if lang == self.source_lang:
                    continue
                if lang == self.target_lang:
                    continue
                other_markers.append(f"[[{lang}:{other_page_title}]]")

            source_interwiki = f"[[{self.source_lang}:{title}]]"
            all_markers = [source_interwiki] + other_markers
            markers_block = '\n'.join(all_markers)
            new_wikitext_with_interwiki = new_wikitext + f"\n{markers_block}\n"

            publish_resp = self.target_mw.create_or_update_page(target_title, new_wikitext_with_interwiki)

            # Add/update interwiki link in source page pointing to target
            target_interwiki = f"[[{self.target_lang}:{target_title}]]"
            self.source_mw.add_or_update_interwiki_link(title, target_interwiki)

            # Propagate English link to other existing language pages and add back-links to English
            for lang, other_page_title in langlinks.items():
                if lang in (self.source_lang, self.target_lang):
                    continue
                # Get or create client
                client = self._other_clients.get(lang)
                if client is None:
                    ep = self._derive_endpoint_for_lang(self.source_mw.endpoint, lang)
                    client = MediaWikiClient(ep, verify_ssl=self.verify_ssl)
                    self._other_clients[lang] = client
                # Add link to English page on that language page
                english_marker = f"[[{self.target_lang}:{target_title}]]"
                try:
                    client.add_or_update_interwiki_link(other_page_title, english_marker, summary='Add English interwiki link')
                except Exception as e:
                    logger.warning('Failed updating interwiki on %s:%s -> %s: %s', lang, other_page_title, target_title, e)
        else:
            publish_resp = {'dry_run': True}
        
        # Add timestamp to log
        date_iso = datetime.now(timezone.utc).isoformat()
        self._append_log([title, target_title, self.source_lang, self.target_lang, 'translated', date_iso, ';'.join(validation.get('issues', []))])
        logger.info('Translated %s -> %s (%s)', title, target_title, 'dry-run' if self.dry_run else 'published')
