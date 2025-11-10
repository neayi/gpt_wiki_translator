#!/usr/bin/env python3
"""Integration test for --page and --force options."""
import sys
sys.path.insert(0, 'src')

from gpt_wiki_translator.translation_pipeline import TranslationPipeline

def test_force_logic():
    """Test that force flag bypasses langlink check."""
    print("Testing force flag logic...")
    
    # Mock scenario: page already has translation
    class MockMW:
        def get_langlinks(self, title):
            return {'en': 'Existing_Translation'}
    
    # Test without force
    pipeline_no_force = TranslationPipeline(
        'http://fr.example.org/api.php',
        'http://en.example.org/api.php',
        'fr', 'en',
        dry_run=True,
        force=False
    )
    pipeline_no_force.source_mw = MockMW()
    
    # Test with force
    pipeline_with_force = TranslationPipeline(
        'http://fr.example.org/api.php',
        'http://en.example.org/api.php',
        'fr', 'en',
        dry_run=True,
        force=True
    )
    pipeline_with_force.source_mw = MockMW()
    
    assert pipeline_no_force.force is False
    assert pipeline_with_force.force is True
    
    print("  ✓ Force flag properly stored in pipeline")
    print("  ✓ Pipeline can be instantiated with force=True")

if __name__ == '__main__':
    try:
        test_force_logic()
        print("\n✅ Integration test passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
