# Mapping des préfixes de namespace FR -> EN (extensible)
NAMESPACE_MAPPING = {
    'Catégorie': 'Category',
    'Fichier': 'File',
    'Modèle': 'Template',
    'Portail': 'Portal',
    'Projet': 'Project',
    'Aide': 'Help',
    'Discussion': 'Talk',
}

def translate_namespace_prefix(title: str, source_lang: str, target_lang: str) -> str:
    """Si le titre commence par un namespace FR connu, le remplace par équivalent EN.
    Ne traduit pas le reste du titre. Ne modifie rien si target_lang != 'en' ou source_lang != 'fr'."""
    if source_lang == 'fr' and target_lang == 'en':
        for fr_prefix, en_prefix in NAMESPACE_MAPPING.items():
            prefix_colon = fr_prefix + ':'
            if title.startswith(prefix_colon):
                return en_prefix + ':' + title[len(prefix_colon):]
    return title
