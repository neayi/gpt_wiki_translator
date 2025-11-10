from gpt_wiki_translator.namespace_mapping import translate_namespace_prefix

def test_translate_namespace_prefix_basic():
    assert translate_namespace_prefix('Catégorie:Blé', 'fr', 'en') == 'Category:Blé'
    assert translate_namespace_prefix('Fichier:Image.jpg', 'fr', 'en') == 'File:Image.jpg'
    assert translate_namespace_prefix('Modèle:Infobox', 'fr', 'en') == 'Template:Infobox'

def test_translate_namespace_prefix_no_change():
    assert translate_namespace_prefix('Category:Wheat', 'fr', 'en') == 'Category:Wheat'
    assert translate_namespace_prefix('Blé', 'fr', 'en') == 'Blé'

def test_translate_namespace_prefix_other_lang():
    assert translate_namespace_prefix('Catégorie:Blé', 'fr', 'de') == 'Catégorie:Blé'
