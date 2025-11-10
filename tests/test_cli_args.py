#!/usr/bin/env python3
"""Test new CLI arguments: --page and --force."""
import sys
sys.path.insert(0, 'src')

from gpt_wiki_translator.cli import parse_args, derive_endpoints_and_title

def test_page_argument():
    """Test --page with URL."""
    print("Testing --page with URL...")
    sys.argv = ['cli.py', '--page', 'https://fr.dev.tripleperformance.ag/wiki/Test', '--target-lang', 'en']
    args = parse_args()
    assert args.page == 'https://fr.dev.tripleperformance.ag/wiki/Test'
    assert args.target_lang == 'en'
    assert args.force is False
    assert args.dry_run is False
    print("  ✓ --page argument parsed correctly")

def test_page_with_force():
    """Test --page with --force."""
    print("\nTesting --page with --force...")
    sys.argv = ['cli.py', '--page', 'Test_Page', '--target-lang', 'en', '--force']
    args = parse_args()
    assert args.page == 'Test_Page'
    assert args.force is True
    print("  ✓ --force flag works")

def test_page_with_dry_run():
    """Test --page with --dry-run."""
    print("\nTesting --page with --dry-run...")
    sys.argv = ['cli.py', '--page', 'Test_Page', '--target-lang', 'en', '--dry-run']
    args = parse_args()
    assert args.page == 'Test_Page'
    assert args.dry_run is True
    print("  ✓ --dry-run flag works")

def test_all_flags():
    """Test all flags combined."""
    print("\nTesting all flags combined...")
    sys.argv = ['cli.py', '--page', 'Test', '--target-lang', 'de', '--force', '--dry-run']
    args = parse_args()
    assert args.force is True
    assert args.dry_run is True
    assert args.target_lang == 'de'
    print("  ✓ All flags work together")

def test_page_url_parsing():
    """Test URL parsing with --page."""
    print("\nTesting URL parsing...")
    url = 'https://fr.dev.tripleperformance.ag/wiki/Test_Page'
    src_ep, tgt_ep, title, src_lang = derive_endpoints_and_title(url, 'en', None)
    assert src_ep == 'https://fr.dev.tripleperformance.ag/api.php'
    assert tgt_ep == 'https://en.dev.tripleperformance.ag/api.php'
    assert title == 'Test_Page'
    assert src_lang == 'fr'
    print("  ✓ URL parsing correct")

if __name__ == '__main__':
    try:
        test_page_argument()
        test_page_with_force()
        test_page_with_dry_run()
        test_all_flags()
        test_page_url_parsing()
        print("\n✅ All CLI argument tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except SystemExit:
        # parse_args() calls sys.exit on error, which is expected for validation tests
        pass
