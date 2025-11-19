import pytest
from gpt_wiki_translator.wikitext_parser import restore_protected_template_params

def test_restore_protected_template_params():
    # Original wikitext with protected and unprotected params
    original = "{{Infobox | image = MyImage.jpg | caption = This is a caption | class = my-class | type de page = Article }}"
    
    # Simulated translation where everything was translated (incorrectly for protected ones)
    # 'image' value changed to 'MonImage.jpg' (should be restored)
    # 'caption' value changed to 'Ceci est une légende' (should stay translated)
    # 'class' value changed to 'ma-classe' (should be restored)
    # 'type de page' changed to 'Article traduit' (should be restored)
    translated = "{{Infobox | image = MonImage.jpg | caption = Ceci est une légende | class = ma-classe | type de page = Article traduit }}"
    
    restored = restore_protected_template_params(original, translated)
    
    # Check protected params are restored
    assert "image = MyImage.jpg" in restored
    assert "class = my-class" in restored
    assert "type de page = Article" in restored
    
    # Check unprotected params remain translated
    assert "caption = Ceci est une légende" in restored

def test_restore_protected_template_params_case_insensitive():
    # Test that param name matching is robust (normalization)
    original = "{{Test | Image = MyImage.jpg }}"
    translated = "{{Test | Image = MonImage.jpg }}"
    
    restored = restore_protected_template_params(original, translated)
    assert "Image = MyImage.jpg" in restored
