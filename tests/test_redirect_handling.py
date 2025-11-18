"""Test redirect handling with --force flag."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.gpt_wiki_translator.translation_pipeline import TranslationPipeline


class TestRedirectHandling:
    """Test that redirects are properly resolved when --force is used."""

    @patch('src.gpt_wiki_translator.translation_pipeline.OpenAIClient')
    @patch('src.gpt_wiki_translator.translation_pipeline.MediaWikiClient')
    def test_force_follows_redirect(self, mock_mw_class, mock_ai_class):
        """When --force is used and target is a redirect, should use the final target page."""
        # Setup mocks
        source_mw = Mock()
        target_mw = Mock()
        ai = Mock()

        mock_mw_class.side_effect = [source_mw, target_mw]
        mock_ai_class.return_value = ai

        # Source page setup
        source_mw.get_langlinks.return_value = {}
        source_mw.fetch_page_wikitext.return_value = "Test content"
        source_mw.add_or_update_interwiki_link.return_value = {'success': True}

        # Target page setup: exists and is a redirect to "Final Target Page"
        target_mw.page_exists.return_value = (True, "Final Target Page")
        target_mw.create_or_update_page.return_value = {'success': True}

        # AI translation setup
        ai.translate_chunk.return_value = "Translated content"
        ai.validate_translation.return_value = '{"issues": []}'

        # Create pipeline with force=True
        pipeline = TranslationPipeline(
            source_endpoint="https://fr.example.com/api.php",
            target_endpoint="https://en.example.com/api.php",
            source_lang="fr",
            target_lang="en",
            dry_run=False,
            force=True
        )

        # Process a page
        pipeline.process_single_page("Test Page")

        # Verify that page_exists was called with resolve_redirects=True (force=True)
        target_mw.page_exists.assert_called_once()
        call_args = target_mw.page_exists.call_args
        assert call_args[1]['resolve_redirects'] == True

        # Verify that the final target page was used (not the redirect)
        target_mw.create_or_update_page.assert_called_once()
        created_title = target_mw.create_or_update_page.call_args[0][0]
        assert created_title == "Final Target Page"

    @patch('src.gpt_wiki_translator.translation_pipeline.OpenAIClient')
    @patch('src.gpt_wiki_translator.translation_pipeline.MediaWikiClient')
    def test_no_force_does_not_follow_redirect(self, mock_mw_class, mock_ai_class):
        """When --force is NOT used, should not follow redirects."""
        # Setup mocks
        source_mw = Mock()
        target_mw = Mock()
        ai = Mock()

        mock_mw_class.side_effect = [source_mw, target_mw]
        mock_ai_class.return_value = ai

        # Source page setup
        source_mw.get_langlinks.return_value = {}
        source_mw.add_or_update_interwiki_link.return_value = {'success': True}

        # Target page setup: exists (redirect not resolved when force=False)
        target_mw.page_exists.return_value = (True, "Test Page EN")

        # Create pipeline with force=False
        pipeline = TranslationPipeline(
            source_endpoint="https://fr.example.com/api.php",
            target_endpoint="https://en.example.com/api.php",
            source_lang="fr",
            target_lang="en",
            dry_run=False,
            force=False
        )

        # Process a page
        pipeline.process_single_page("Test Page")

        # Verify that page_exists was called with resolve_redirects=False (force=False)
        target_mw.page_exists.assert_called_once()
        call_args = target_mw.page_exists.call_args
        assert call_args[1]['resolve_redirects'] == False

        # Verify that no translation occurred (target exists, no force)
        source_mw.fetch_page_wikitext.assert_not_called()
        target_mw.create_or_update_page.assert_not_called()
