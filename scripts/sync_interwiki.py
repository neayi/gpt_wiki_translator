#!/usr/bin/env python3
"""Synchronise interlanguage (interwiki) links across all translated pages of a wiki.

Usage:
  python scripts/sync_interwiki.py --endpoint https://fr.tripleperformance.ag/api.php [--dry-run] [--limit 500]
  python scripts/sync_interwiki.py --page https://fr.tripleperformance.ag/wiki/Abutilon [--dry-run]

Logic:
  1. Iterate all pages (generator=allpages) that have langlinks OR use single page from --page URL.
  2. For each seed page build a translation cluster: fetch langlinks of the seed and of each translated page.
  3. Compute the union mapping lang -> title across the cluster.
  4. For every page in the cluster ensure it contains the full set of interwiki links with correct targets.
     Perform at most ONE edit per page (batch replacement/appending).
  5. Skip clusters already processed (signature = frozenset of lang:title pairs).

Notes:
  - Assumes same domain pattern where first subdomain is language code (fr., en., es., etc.).
  - Credentials taken from existing configuration (env vars).
  - Dry-run prints intended changes without editing pages.
  - When --page is used, endpoint is derived from URL and only that page's cluster is processed.
"""
from __future__ import annotations
import argparse
import re
import sys
from typing import Dict, Set, Tuple, List
from urllib.parse import urlparse, urlunparse

from gpt_wiki_translator.config import get_settings
from gpt_wiki_translator.mediawiki_client import MediaWikiClient
from gpt_wiki_translator.logging_utils import get_logger

logger = get_logger()

# Cache for interwiki prefixes per endpoint
_interwiki_prefixes_cache: Dict[str, Set[str]] = {}

def get_valid_interwiki_prefixes(client: MediaWikiClient) -> Set[str]:
    """Fetch valid interwiki prefixes from MediaWiki API.
    Returns only prefixes whose URLs contain 'tripleperformance'.
    Results are cached per endpoint.
    """
    if client.endpoint in _interwiki_prefixes_cache:
        return _interwiki_prefixes_cache[client.endpoint]
    
    params = {
        'action': 'query',
        'meta': 'siteinfo',
        'siprop': 'interwikimap',
        'format': 'json'
    }
    r = client.session.get(client.endpoint, params=params, timeout=30, verify=client.verify_ssl)
    r.raise_for_status()
    data = r.json()
    
    prefixes: Set[str] = set()
    interwikimap = data.get('query', {}).get('interwikimap', [])
    for entry in interwikimap:
        url = entry.get('url', '')
        prefix = entry.get('prefix', '')
        if 'tripleperformance' in url.lower() and prefix:
            prefixes.add(prefix)
    
    _interwiki_prefixes_cache[client.endpoint] = prefixes
    logger.debug('Loaded %d interwiki prefixes for %s: %s', len(prefixes), client.endpoint, ', '.join(sorted(prefixes)))
    return prefixes

def get_interwiki_pattern(client: MediaWikiClient) -> re.Pattern:
    """Build regex pattern matching only valid interwiki links for this endpoint."""
    prefixes = get_valid_interwiki_prefixes(client)
    if not prefixes:
        # Fallback to empty pattern that matches nothing
        return re.compile(r'(?!.*)')
    # Build pattern: [[prefix:Page]] or [[:prefix:Page]]
    prefix_group = '|'.join(re.escape(p) for p in prefixes)
    return re.compile(rf"\[\[:?({prefix_group}):([^\]]+)\]\]")

def parse_mediawiki_url(url: str) -> Tuple[str, str]:
    """Parse MediaWiki page URL and return (api_endpoint, page_title).
    
    Examples:
      https://fr.tripleperformance.ag/wiki/Abutilon
        -> ('https://fr.tripleperformance.ag/api.php', 'Abutilon')
      https://en.example.org/w/index.php?title=Main_Page
        -> ('https://en.example.org/w/api.php', 'Main_Page')
    """
    import urllib.parse
    parsed = urlparse(url)
    
    # Extract title from URL
    if '/wiki/' in parsed.path:
        # Format: /wiki/Page_Title
        title = parsed.path.split('/wiki/', 1)[1]
        # Decode URL encoding (e.g., %C3%A9 -> é)
        title = urllib.parse.unquote(title)
    elif 'title=' in parsed.query:
        # Format: /w/index.php?title=Page_Title
        query_params = urllib.parse.parse_qs(parsed.query)
        title = query_params.get('title', [''])[0]
    else:
        raise ValueError(f"Cannot extract page title from URL: {url}")
    
    # Build API endpoint
    if '/wiki/' in parsed.path:
        # Replace /wiki/ with /api.php
        api_path = parsed.path.rsplit('/wiki/', 1)[0] + '/api.php'
    elif '/w/index.php' in parsed.path:
        # Replace /w/index.php with /w/api.php
        api_path = parsed.path.replace('/index.php', '/api.php')
    else:
        # Default: assume /api.php at root
        api_path = '/api.php'
    
    endpoint = urlunparse((parsed.scheme, parsed.netloc, api_path, '', '', ''))
    
    return endpoint, title


def derive_endpoint_for_lang(base_endpoint: str, lang: str) -> str:
    p = urlparse(base_endpoint)
    parts = p.netloc.split('.')
    if parts:
        parts[0] = lang
    netloc = '.'.join(parts)
    return urlunparse((p.scheme, netloc, p.path, '', '', ''))


def fetch_pages_with_langlinks(client: MediaWikiClient, limit: int | None, from_page: str | None = None) -> List[str]:
    """Return list of page titles that have at least one langlink.
    Uses generator=allpages with prop=langlinks and continuation.
    
    Args:
        client: MediaWiki client
        limit: Maximum number of pages to fetch
        from_page: Start fetching from this page title (uses gapfrom parameter)
    """
    titles: List[str] = []
    continue_params = {}
    fetched = 0
    while True:
        params = {
            'action': 'query',
            'generator': 'allpages',
            'gaplimit': '1000',
            'prop': 'langlinks',
            'format': 'json'
        }
        # Add continuation parameters from previous response
        params.update(continue_params)
        
        # Use gapfrom on first request only (when no continue params)
        if not continue_params and from_page:
            params['gapfrom'] = from_page
            
        r = client.session.get(client.endpoint, params=params, timeout=30, verify=client.verify_ssl)
        r.raise_for_status()
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        for page in pages.values():
            if 'langlinks' in page:
                titles.append(page['title'])
                fetched += 1
                if limit and fetched >= limit:
                    return titles
        
        # Get entire continue structure for next request
        continue_params = data.get('continue', {})
        
        if not continue_params:
            break
    return titles


def get_langlinks_map(client: MediaWikiClient, title: str) -> Dict[str, str]:
    return client.get_langlinks(title)


def build_cluster(seed_title: str, seed_lang: str, seed_client: MediaWikiClient) -> Dict[str, str]:
    """Build a raw translation cluster mapping lang -> page title by exploring langlinks.
    Resolves redirects to final target pages.
    """
    # Resolve seed page if it's a redirect
    resolved_seed = seed_client.resolve_redirect(seed_title)
    if not resolved_seed:
        logger.warning('Seed page %s:%s does not exist, skipping cluster', seed_lang, seed_title)
        return {}
    seed_title = resolved_seed
    
    cluster: Dict[str, str] = {seed_lang: seed_title}
    to_visit: List[Tuple[str, str]] = [(seed_lang, seed_title)]
    visited: Set[Tuple[str, str]] = set()
    while to_visit:
        lang, title = to_visit.pop()
        if (lang, title) in visited:
            continue
        visited.add((lang, title))
        if lang == seed_lang:
            client = seed_client
        else:
            ep = derive_endpoint_for_lang(seed_client.endpoint, lang)
            client = MediaWikiClient(ep, verify_ssl=seed_client.verify_ssl)
        
        # Resolve redirect if needed
        resolved_title = client.resolve_redirect(title)
        if not resolved_title:
            logger.warning('Page %s:%s does not exist, skipping', lang, title)
            continue
        if resolved_title != title:
            logger.info('Resolved redirect %s:%s -> %s', lang, title, resolved_title)
            title = resolved_title
            cluster[lang] = title  # Update cluster with resolved title
        
        links = get_langlinks_map(client, title)
        for llang, ltitle in links.items():
            if llang not in cluster:
                # Resolve redirect for discovered langlink
                llang_ep = derive_endpoint_for_lang(seed_client.endpoint, llang)
                llang_client = MediaWikiClient(llang_ep, verify_ssl=seed_client.verify_ssl)
                resolved_ltitle = llang_client.resolve_redirect(ltitle)
                if not resolved_ltitle:
                    logger.warning('Langlink target %s:%s does not exist, skipping', llang, ltitle)
                    continue
                if resolved_ltitle != ltitle:
                    logger.info('Resolved redirect %s:%s -> %s', llang, ltitle, resolved_ltitle)
                    ltitle = resolved_ltitle
                cluster[llang] = ltitle
                to_visit.append((llang, ltitle))
    return cluster

def filter_existing_pages(seed_client: MediaWikiClient, endpoint: str, cluster: Dict[str, str]) -> Dict[str, str]:
    """Return subset of cluster retaining only pages that actually exist on their language wiki.
    Resolves redirects to final target pages and updates cluster with resolved titles.
    """
    existing: Dict[str, str] = {}
    for lang, title in cluster.items():
        ep = derive_endpoint_for_lang(endpoint, lang)
        client = MediaWikiClient(ep, verify_ssl=seed_client.verify_ssl)
        # Resolve redirect to final page (returns None if page doesn't exist)
        resolved_title = client.resolve_redirect(title)
        if resolved_title:
            if resolved_title != title:
                logger.info('Resolved redirect %s:%s -> %s', lang, title, resolved_title)
            existing[lang] = resolved_title
        else:
            logger.info('Prune interwiki link %s:%s (target page does not exist)', lang, title)
    return existing


def parse_existing_interwiki(content: str, client: MediaWikiClient) -> Dict[str, str]:
    """Parse existing interwiki links using valid prefixes for this endpoint."""
    mapping: Dict[str, str] = {}
    pattern = get_interwiki_pattern(client)
    for m in pattern.finditer(content):
        mapping[m.group(1)] = m.group(2)
    return mapping


def ensure_links_on_page(client: MediaWikiClient, title: str, required: Dict[str, str], self_lang: str, dry_run: bool) -> bool:
    """Ensure page has required interwiki links (excluding self language).
    Skip modification if all required links already exist with correct targets.
    Returns True if an edit is performed.
    """
    content = client.fetch_page_wikitext(title) or ''
    existing = parse_existing_interwiki(content, client)  # lang -> ptitle

    # Build expected mapping excluding self language
    expected = {lang: ptitle for lang, ptitle in required.items() if lang != self_lang}
    # Filter existing excluding self
    existing_filtered = {lang: ptitle for lang, ptitle in existing.items() if lang != self_lang}

    # If exact match (no missing, no extra), skip
    if existing_filtered == expected:
        logger.info('Skip %s (interwiki set complete)', title)
        return False

    # Build marker block only for expected (exclude self)
    markers = [f"[[{lang}:{ptitle}]]" for lang, ptitle in sorted(expected.items())]
    unified_block = '\n'.join(markers)

    # Remove old interwiki markers (any language) then append new block
    interwiki_pattern = get_interwiki_pattern(client)
    cleaned = interwiki_pattern.sub('', content)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).rstrip()
    new_content = cleaned + ('\n' if not cleaned.endswith('\n') else '') + unified_block + '\n'

    if dry_run:
        missing = [lang for lang in expected.keys() if lang not in existing]
        logger.info('[DRY-RUN] Would update %s: +%d links (missing: %s)', title, len(expected), ','.join(missing) or 'none')
        return True
    else:
        client.create_or_update_page(title, new_content, summary='Sync interlanguage links')
        logger.info('Updated interwiki links on %s (%d total, excluding self)', title, len(expected))
        return True


def sync(endpoint: str, dry_run: bool, limit: int | None, from_page: str | None = None):
    settings = get_settings()
    seed_client = MediaWikiClient(endpoint, verify_ssl=not endpoint.startswith('https://') or '.dev.' not in endpoint)
    page_titles = fetch_pages_with_langlinks(seed_client, limit, from_page)
    
    if from_page:
        logger.info('Found %d seed pages with langlinks (starting from "%s")', len(page_titles), from_page)
    else:
        logger.info('Found %d seed pages with langlinks', len(page_titles))
    
    processed_clusters: Set[frozenset] = set()
    total_pages_touched = 0

    for seed_title in page_titles:
        cluster = build_cluster(seed_title, settings.source_language if hasattr(settings, 'source_language') else endpoint.split('//')[1].split('.')[0], seed_client)
        signature = frozenset(f"{lang}:{title}" for lang, title in cluster.items())
        if signature in processed_clusters:
            continue
        processed_clusters.add(signature)
        logger.info('Cluster for %s: %s', seed_title, ', '.join(f"{l}:{t}" for l,t in cluster.items()))
        # For each page ensure interwiki block
        # Remove links whose target pages do not exist
        existing_cluster = filter_existing_pages(seed_client, endpoint, cluster)
        for lang, title in cluster.items():
            ep = derive_endpoint_for_lang(endpoint, lang)
            client = MediaWikiClient(ep, verify_ssl=seed_client.verify_ssl)
            # Use existing_cluster so that non-existent targets are removed
            changed = ensure_links_on_page(client, title, existing_cluster, lang, dry_run)
            if changed:
                total_pages_touched += 1

    logger.info('Synchronization complete. Pages modified: %d', total_pages_touched)


def main():
    parser = argparse.ArgumentParser(description='Synchronize interlanguage links across all translated pages.')
    parser.add_argument('--endpoint', help='MediaWiki API endpoint of the source wiki (e.g. https://fr.tripleperformance.ag/api.php)')
    parser.add_argument('--page', help='MediaWiki page URL to process (e.g. https://fr.tripleperformance.ag/wiki/Abutilon). Endpoint is derived from URL.')
    parser.add_argument('--dry-run', action='store_true', help='Do not perform edits, only report actions')
    parser.add_argument('--limit', type=int, help='Limit number of seed pages processed (only when using --endpoint)')
    parser.add_argument('--from', dest='from_page', help='Resume from this page title (only when using --endpoint)')
    args = parser.parse_args()
    
    if args.page and args.endpoint:
        parser.error('Cannot specify both --page and --endpoint. Use --page alone to process a single page.')
    if not args.page and not args.endpoint:
        parser.error('Must specify either --page (URL) or --endpoint (API endpoint).')
    
    if args.page:
        # Single page mode: derive endpoint and title from URL
        endpoint, page_title = parse_mediawiki_url(args.page)
        logger.info('Single page mode: %s (endpoint: %s)', page_title, endpoint)
        settings = get_settings()
        seed_client = MediaWikiClient(endpoint, verify_ssl=not endpoint.startswith('https://') or '.dev.' not in endpoint)
        # Extract language from endpoint (first subdomain)
        lang = endpoint.split('//')[1].split('.')[0]
        cluster = build_cluster(page_title, lang, seed_client)
        logger.info('Cluster for %s: %s', page_title, ', '.join(f"{l}:{t}" for l,t in cluster.items()))
        existing_cluster = filter_existing_pages(seed_client, endpoint, cluster)
        total_pages_touched = 0
        for lang, title in existing_cluster.items():
            ep = derive_endpoint_for_lang(endpoint, lang)
            client = MediaWikiClient(ep, verify_ssl=seed_client.verify_ssl)
            changed = ensure_links_on_page(client, title, existing_cluster, lang, args.dry_run)
            if changed:
                total_pages_touched += 1
        logger.info('Synchronization complete. Pages modified: %d', total_pages_touched)
    else:
        # Batch mode: iterate all pages with langlinks
        sync(args.endpoint, args.dry_run, args.limit, args.from_page)

if __name__ == '__main__':
    main()
