# Architecture Technique

## Vue d'ensemble

Le projet est structuré en modules Python indépendants pour faciliter la maintenance et les tests.

## Modules principaux

### `config.py`
- Gestion centralisée de la configuration via `pydantic-settings`
- Chargement des variables d'environnement depuis `.env`
- Pas de langues codées en dur (source/target dérivées des URLs)

### `cli.py`
- Point d'entrée principal (`python -m gpt_wiki_translator`)
- Parsing des arguments: `--input`, `--target-lang`, `--dry-run`
- Dérivation automatique des endpoints:
  - URLs complètes → extraction du scheme, host, titre
  - Préservation automatique du segment `.dev.` ou prod
  - Groupement des pages par couple (source_endpoint, target_endpoint) pour efficacité
- Détection automatique de `source_lang` depuis le premier label du host

### `mediawiki_client.py`
- Wrapper autour de l'API MediaWiki
- Méthodes principales:
  - `login()`: Authentification (action=login legacy)
  - `fetch_page_wikitext()`: Récupération du contenu brut
  - `get_langlinks()`: Détection des traductions existantes
  - `create_or_update_page()`: Publication
  - `add_or_update_interwiki_link()`: Ajout du lien interwiki sur la source
- Gestion CSRF token (récupération + cache)
- Session HTTP persistante pour performance

### `openai_client.py`
- Wrapper autour de l'API OpenAI
- `translate_chunk()`: Traduction avec prompt système strict
- `validate_translation()`: Validation post-traduction (retour JSON)
- Retry automatique via `tenacity` (3 tentatives, backoff exponentiel)

### `wikitext_parser.py`
- Parsing AST via `mwparserfromhell`
- Segmentation du wikitext:
  - Éléments protégés (templates, liens, balises) → non traduits
  - Texte libre → traduit
- Reconstruction post-traduction en préservant la structure
- Heuristiques de validation (comptage `{{`, `[[`)

### `namespace_mapping.py`
- Table de correspondance FR ↔ EN pour préfixes de namespace
- Ex: `Catégorie:` → `Category:`, `Fichier:` → `File:`
- Appliqué uniquement aux titres (pas au contenu de wikitext)

### `translation_pipeline.py`
- Orchestrateur principal
- Flux par page:
  1. Vérifier si traduction existe (`langlinks`)
  2. Récupérer wikitext source
  3. Segmenter (protéger templates/fichiers)
  4. Traduire segments textuels
  5. Reconstruire
  6. Validation locale + OpenAI
  7. Publier sur wiki cible (sauf dry-run)
  8. Ajouter lien interwiki sur source
  9. Journaliser dans CSV
- Support dry-run transparent

### `logging_utils.py`
- Logger structuré
- Création automatique du répertoire `logs/`
- CSV append-only pour traçabilité

## Flux de données

```
Input file (URLs)
    ↓
CLI: parse URLs, dérive endpoints (source, target)
    ↓
Pipeline: groupe par endpoints
    ↓
Pour chaque page:
    ↓
    MediaWikiClient (source): get_langlinks()
    → Si existe, skip
    ↓
    MediaWikiClient (source): fetch_page_wikitext()
    ↓
    WikitextParser: segment_wikitext() → [protected, text, protected, text...]
    ↓
    OpenAIClient: translate_chunk() pour chaque segment texte
    ↓
    WikitextParser: merge_translated()
    ↓
    Validation locale (braces, brackets)
    ↓
    OpenAIClient: validate_translation() → JSON
    ↓
    namespace_mapping: translate_namespace_prefix(title)
    ↓
    MediaWikiClient (target): create_or_update_page()
    ↓
    MediaWikiClient (source): add_or_update_interwiki_link()
    ↓
    CSV log: append row
```

## Gestion des environnements (prod/dev)

- **Entrée**: URLs avec sous-domaine de langue (ex: `fr.dev.tripleperformance.ag`)
- **Traitement**: `swap_lang_in_host()` remplace uniquement le premier label
  - `fr.dev.example.com` → `en.dev.example.com`
  - `fr.example.com` → `en.example.com`
- **Résultat**: Traductions publiées sur le même environnement

## Points d'extension futurs

1. **Chunking avancé**: Découper les pages > 1800 tokens par section/paragraphe
2. **Parsing fin des images**: Traduire légendes tout en gardant noms de fichiers intacts
3. **Cache de traduction**: SQLite ou shelve pour segments déjà traduits
4. **Validation stricte**: Compter templates, vérifier paramètres, détecter altération
5. **Authentification moderne**: Support `clientlogin` et OAuth
6. **Parallélisation**: asyncio pour traduire plusieurs pages simultanément
7. **Retry intelligent**: Backoff adaptatif selon rate-limits MediaWiki

## Dépendances critiques

- `mwparserfromhell`: Parsing AST Wikitext fiable
- `openai`: SDK officiel pour GPT
- `pydantic-settings`: Config typée et validée
- `tenacity`: Retry patterns robustes
- `tqdm`: UI de progression

## Tests

- `tests/test_namespace_mapping.py`: Mapping préfixes
- `tests/test_smoke.py`: Tests d'intégration CLI (parsing URLs, swap host)
- `scripts/check_config.py`: Validation configuration avant exécution

## Sécurité

- Clés API dans `.env` (git-ignoré)
- Pas de secrets hardcodés
- Session HTTP avec timeouts
- Validation des entrées utilisateur (URLs, titres)
