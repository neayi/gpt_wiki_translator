import argparse
from pathlib import Path
from urllib.parse import urlparse, unquote
from .translation_pipeline import TranslationPipeline
from .config import get_settings

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Translate MediaWiki pages using OpenAI while preserving structure.')
    p.add_argument('--input', help='Path to txt file with one page title or URL per line')
    p.add_argument('--page', help='Single page title or URL to translate (alternative to --input)')
    p.add_argument('--target-lang', required=True, help='Target language code (e.g., en, de) used to select the destination wiki subdomain')
    p.add_argument('--dry-run', action='store_true', help='Do not publish translated pages, just simulate')
    p.add_argument('--force', action='store_true', help='Force retranslation even if target page already exists')
    p.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL certificate verification (useful for dev environments)')
    args = p.parse_args()
    
    # Validate that either --input or --page is provided
    if not args.input and not args.page:
        p.error('Either --input or --page must be specified')
    if args.input and args.page:
        p.error('Cannot specify both --input and --page')
    
    return args

def swap_lang_in_host(host: str, target_lang: str) -> str:
    """Replace only the language subdomain (first part) while preserving .dev. or prod segments.
    Examples:
      fr.tripleperformance.ag -> en.tripleperformance.ag
      fr.dev.tripleperformance.ag -> en.dev.tripleperformance.ag
    """
    parts = host.split('.')
    if len(parts) >= 2:
        parts[0] = target_lang
    return '.'.join(parts)

def derive_endpoints_and_title(line: str, target_lang: str, default_endpoint: str | None) -> tuple[str, str, str, str]:
    """Return (source_endpoint, target_endpoint, title, source_lang) for a line.
    If line is URL, derive endpoints from URL host (assume /api.php).
    Else use default_endpoint for source and swap host for target.
    Also returns decoded title from URL if applicable and source_lang inferred from host.
    """
    line = line.strip()
    if line.startswith('http'):
        u = urlparse(line)
        # title
        if '/wiki/' in u.path:
            title = unquote(u.path.split('/wiki/', 1)[1])
        else:
            title = unquote(u.path.lstrip('/'))
        source_endpoint = f"{u.scheme}://{u.netloc}/api.php"
        target_host = swap_lang_in_host(u.netloc, target_lang)
        target_endpoint = f"{u.scheme}://{target_host}/api.php"
        source_lang = u.netloc.split('.', 1)[0]
        return source_endpoint, target_endpoint, title, source_lang
    else:
        if not default_endpoint:
            raise ValueError('A default MEDIAWIKI_API_ENDPOINT must be set in .env for non-URL lines')
        # Extract host to compute target
        u = urlparse(default_endpoint)
        title = line
        source_endpoint = default_endpoint
        target_host = swap_lang_in_host(u.netloc, target_lang)
        target_endpoint = f"{u.scheme}://{target_host}{u.path}"
        source_lang = u.netloc.split('.', 1)[0]
        return source_endpoint, target_endpoint, title, source_lang

def main():
    args = parse_args()
    settings = get_settings()
    # Build list of (source_endpoint, target_endpoint, title, source_lang)
    entries: list[tuple[str, str, str, str]] = []
    
    if args.page:
        # Single page mode
        source_ep, target_ep, title, source_lang = derive_endpoints_and_title(args.page, args.target_lang, settings.mediawiki_api_endpoint)
        entries.append((source_ep, target_ep, title, source_lang))
    else:
        # Batch mode from file
        p = Path(args.input)
        for raw in p.read_text(encoding='utf-8').splitlines():
            raw = raw.strip()
            if not raw or raw.startswith('#'):
                continue
            source_ep, target_ep, title, source_lang = derive_endpoints_and_title(raw, args.target_lang, settings.mediawiki_api_endpoint)
            entries.append((source_ep, target_ep, title, source_lang))

    # Group by source/target endpoints to reuse clients per batch for efficiency
    from collections import defaultdict
    groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)  # (source_ep, target_ep, source_lang) -> titles
    for source_ep, target_ep, title, source_lang in entries:
        groups[(source_ep, target_ep, source_lang)].append(title)

    for (source_ep, target_ep, source_lang), titles in groups.items():
        # Auto-detect dev environment and disable SSL verification if requested or if .dev. is in endpoint
        verify_ssl = not args.no_verify_ssl and '.dev.' not in source_ep
        pipeline = TranslationPipeline(
            source_ep, target_ep, source_lang, args.target_lang, 
            dry_run=args.dry_run, force=args.force, verify_ssl=verify_ssl
        )
        pipeline.process_pages(titles)

if __name__ == '__main__':
    main()
