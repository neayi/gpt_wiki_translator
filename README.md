# gpt_wiki_translator

Outil de traduction automatisée de pages MediaWiki (ex: wiki francophone vers anglais) s'appuyant sur l'API OpenAI tout en préservant strictement la structure Wikitext (templates, liens, fichiers, mise en forme).

## Objectifs
1. Lire une liste d'URLs de pages source et une langue cible.
2. Vérifier si une traduction existe déjà (interwiki/langlinks) – ignorer si présent.
3. Récupérer le wikitext brut de la page source via l'API MediaWiki.
4. Segmenter et traduire uniquement le texte « visible » en conservant:
	 - Templates (noms + paramètres) non traduits
	 - Fonctions / parser functions intactes
	 - Noms de fichiers/images inchangés
	 - Structure (titres, gras, italique, listes, tableaux)
	 - Préfixes de namespace traduits (Catégorie: -> Category:, Fichier: -> File:, etc.)
5. Validation automatique de la traduction (second prompt + heuristiques locales).
6. Publication sur le wiki cible + ajout d'un lien interwiki dans la page source.
7. Journalisation CSV (source, cible, date, statut) + cache pour éviter retraductions.

## Stack Technique (Option A – Python)
Librairies principales:
- `mwparserfromhell` : parsing AST fiable du Wikitext.
- `requests` : appels MediaWiki API.
- `openai` : traduction + validation.
- `python-dotenv` / `pydantic` : gestion configuration.
- `tenacity` : retries robustes.
- `tqdm` : progression CLI.

## Structure Projet (préliminaire)
```
src/gpt_wiki_translator/
	cli.py
	config.py
	mediawiki_client.py
	openai_client.py
	wikitext_parser.py
	translation_pipeline.py
	namespace_mapping.py
	logging_utils.py
tests/
requirements.txt
.env.example
```

## Configuration (.env)
Voir `.env.example` pour les variables nécessaires: clés API OpenAI & MediaWiki, modèle. Les wikis sont adressés par sous-domaine de langue (fr., en., …). Pas besoin de définir SOURCE/TARGET_LANG dans l'environnement; passe la langue cible à la CLI.

## Démarrage rapide

📖 **Voir [QUICKSTART.md](QUICKSTART.md) pour un guide complet étape par étape**  
📚 **Voir [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) pour des exemples d'utilisation détaillés**

```bash
# Installation rapide
pip install -r requirements.txt
cp .env.example .env
# Éditer .env avec vos clés API

# Vérifier la configuration
python scripts/check_config.py

# Test sur une seule page (recommandé pour débuter)
./translate.sh --page "https://fr.dev.tripleperformance.ag/wiki/Test" --target-lang en --dry-run

# Traduction par lot depuis un fichier
./translate.sh --input data/example_pages.txt --target-lang en --dry-run

# Forcer la retraduction d'une page existante
./translate.sh --page "Page_à_retraduire" --target-lang en --force

# Production (sans --dry-run)
./translate.sh --input data/example_pages.txt --target-lang en
```

### Modes d'utilisation

#### Mode page unique (--page)
Idéal pour tester ou traduire une seule page:
```bash
./translate.sh --page "https://fr.dev.tripleperformance.ag/wiki/Ma_Page" --target-lang en --dry-run
```

#### Mode par lot (--input)
Pour traduire plusieurs pages depuis un fichier:
```bash
./translate.sh --input data/pages.txt --target-lang en
```

### Format du fichier d'entrée
Le fichier `pages.txt` peut contenir:
- **URLs complètes** (recommandé): L'environnement (prod/dev) est automatiquement préservé
  - Production: `https://fr.tripleperformance.ag/wiki/Blé` → `https://en.tripleperformance.ag/wiki/Wheat`
  - Dev: `https://fr.dev.tripleperformance.ag/wiki/Blé` → `https://en.dev.tripleperformance.ag/wiki/Wheat`
- **Titres bruts**: Nécessite `MEDIAWIKI_API_ENDPOINT` dans `.env` comme endpoint source par défaut

Voir `data/example_pages.txt` pour des exemples.

### Options avancées

- **--force**: Force la retraduction même si la page cible existe déjà
  ```bash
  ./translate.sh --page "Ma_Page" --target-lang en --force
  ```
- **--dry-run**: Simule la traduction sans publier (recommandé pour tester)
  ```bash
  ./translate.sh --input pages.txt --target-lang en --dry-run
  ```
- **--no-verify-ssl**: Désactive la vérification SSL (automatique pour `.dev.`)
  ```bash
  ./translate.sh --page "Test" --target-lang en --no-verify-ssl
  ```
  
  **Note**: La vérification SSL est automatiquement désactivée pour les URLs contenant `.dev.` (environnement de développement).

**Important**: Quand vous utilisez des URLs en `.dev.`, les traductions seront automatiquement créées sur l'environnement dev correspondant (ex: `en.dev.tripleperformance.ag`). De même, les URLs prod resteront en prod. Vous pouvez mélanger les deux types d'URLs dans le même fichier d'entrée.

## Tests
```bash
# Lancer les tests de base
python tests/test_smoke.py

# Test du mapping de namespace
python -c "import sys; sys.path.insert(0, 'src'); from gpt_wiki_translator.namespace_mapping import translate_namespace_prefix; print(translate_namespace_prefix('Catégorie:Test', 'fr', 'en'))"
```

## Statut
✅ Architecture et squelette complet
✅ Support multi-environnements (prod/dev)
✅ CLI avec parsing d'URLs
✅ Client MediaWiki avec authentification
🚧 Parsing Wikitext avancé (amélioration en cours)
🚧 Chunking intelligent par tokens
🚧 Validation renforcée des traductions

## Licence
Voir fichier `LICENSE`.

---
Contributions / améliorations bienvenues : tests supplémentaires, prise en charge de langues additionnelles, optimisation coût des prompts.
