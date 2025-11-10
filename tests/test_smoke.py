#!/usr/bin/env python3
"""Quick smoke test for CLI parsing and environment detection."""
import sys
sys.path.insert(0, 'src')

from gpt_wiki_translator.cli import derive_endpoints_and_title, swap_lang_in_host

def test_swap_lang_in_host():
    """Test language subdomain swap preserves dev/prod."""
    tests = [
        ('fr.tripleperformance.ag', 'en', 'en.tripleperformance.ag'),
        ('fr.dev.tripleperformance.ag', 'en', 'en.dev.tripleperformance.ag'),
        ('es.dev.tripleperformance.ag', 'de', 'de.dev.tripleperformance.ag'),
    ]
    for host, target_lang, expected in tests:
        result = swap_lang_in_host(host, target_lang)
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"✓ {host} → {result}")

def test_derive_endpoints_and_title():
    """Test URL parsing and endpoint generation."""
    tests = [
        (
            'https://fr.tripleperformance.ag/wiki/Bl%C3%A9',
            'en',
            'https://fr.tripleperformance.ag/api.php',
            'https://en.tripleperformance.ag/api.php',
            'Blé',
            'fr'
        ),
        (
            'https://fr.dev.tripleperformance.ag/wiki/Test',
            'en',
            'https://fr.dev.tripleperformance.ag/api.php',
            'https://en.dev.tripleperformance.ag/api.php',
            'Test',
            'fr'
        ),
    ]
    for url, target_lang, exp_src, exp_tgt, exp_title, exp_lang in tests:
        src, tgt, title, lang = derive_endpoints_and_title(url, target_lang, None)
        assert src == exp_src, f"Source: expected {exp_src}, got {src}"
        assert tgt == exp_tgt, f"Target: expected {exp_tgt}, got {tgt}"
        assert title == exp_title, f"Title: expected {exp_title}, got {title}"
        assert lang == exp_lang, f"Lang: expected {exp_lang}, got {lang}"
        print(f"✓ {url} parsed correctly")

if __name__ == '__main__':
    print("Testing swap_lang_in_host...")
    test_swap_lang_in_host()
    print("\nTesting derive_endpoints_and_title...")
    test_derive_endpoints_and_title()
    print("\n✅ All smoke tests passed!")
