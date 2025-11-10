# Guide de Démarrage Rapide

## Installation (5 minutes)

### 1. Cloner et préparer l'environnement

```bash
cd /home/bertrand/gpt_wiki_translator

# Créer et activer l'environnement virtuel (déjà fait)
# python3 -m venv .venv
# source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configurer les clés API

```bash
# Copier le template
cp .env.example .env

# Éditer avec vos clés
nano .env  # ou votre éditeur préféré
```

Variables essentielles:
- `OPENAI_API_KEY`: Votre clé OpenAI
- `MEDIAWIKI_USERNAME`: Nom d'utilisateur bot MediaWiki
- `MEDIAWIKI_PASSWORD`: Mot de passe bot
- `MEDIAWIKI_API_ENDPOINT`: (optionnel) Endpoint par défaut si vous utilisez des titres bruts

### 3. Vérifier la configuration

```bash
python scripts/check_config.py
```

Si tout est vert ✅, vous êtes prêt !

## Premier test (mode dry-run)

### Option A: Test sur une seule page (recommandé pour débuter)

```bash
PYTHONPATH=src python -m gpt_wiki_translator.cli \
  --page "https://fr.dev.tripleperformance.ag/wiki/Ma_Page_Test" \
  --target-lang en \
  --dry-run
```

Ou avec un titre simple (si `MEDIAWIKI_API_ENDPOINT` est configuré):
```bash
PYTHONPATH=src python -m gpt_wiki_translator.cli \
  --page "Ma_Page_Test" \
  --target-lang en \
  --dry-run
```

### Option B: Test par lot depuis un fichier

1. Créer un fichier d'entrée `data/my_pages.txt`:
```
https://fr.dev.tripleperformance.ag/wiki/Page_Test_1
https://fr.dev.tripleperformance.ag/wiki/Page_Test_2
```

2. Lancer en mode simulation:
```bash
PYTHONPATH=src python -m gpt_wiki_translator.cli \
  --input data/my_pages.txt \
  --target-lang en \
  --dry-run
```

Le mode `--dry-run`:
- ✅ Récupère les pages source
- ✅ Traduit avec OpenAI
- ✅ Valide la structure
- ❌ Ne publie PAS sur le wiki
- ✅ Génère les logs

### 3. Vérifier les logs

```bash
cat logs/translated_log.csv
```

Format: `source_page,target_page,source_lang,target_lang,status,date_iso,notes`

## Production (traduction réelle)

Une fois satisfait du dry-run, retirez le flag:

```bash
# Page unique
PYTHONPATH=src python -m gpt_wiki_translator.cli \
  --page "Ma_Page" \
  --target-lang en

# Ou par lot
PYTHONPATH=src python -m gpt_wiki_translator.cli \
  --input data/my_pages.txt \
  --target-lang en
```

Cela va:
1. Traduire les pages
2. Les publier sur `en.dev.tripleperformance.ag` (ou prod selon l'URL)
3. Ajouter les liens interwiki sur les sources
4. Journaliser les résultats

### Retraduire une page existante

Si une page a déjà été traduite mais que vous voulez la retraduire (ex: après amélioration des prompts):

```bash
PYTHONPATH=src python -m gpt_wiki_translator.cli \
  --page "Ma_Page" \
  --target-lang en \
  --force
```

Le flag `--force` ignore la vérification des langlinks existants et retraduit la page.

## Environnements prod vs dev

L'outil détecte automatiquement l'environnement depuis l'URL:

- **Dev**: `https://fr.dev.tripleperformance.ag/wiki/X` → `https://en.dev.tripleperformance.ag/wiki/X`
- **Prod**: `https://fr.tripleperformance.ag/wiki/X` → `https://en.tripleperformance.ag/wiki/X`

Vous pouvez mélanger les deux dans le même fichier d'entrée !

## Résolution de problèmes

### Erreur "Import pydantic_settings could not be resolved"
```bash
pip install pydantic-settings
```

### Erreur "No module named 'gpt_wiki_translator'"
Assurez-vous d'être dans le bon répertoire et que le virtualenv est activé:
```bash
cd /home/bertrand/gpt_wiki_translator
source .venv/bin/activate
```

### Erreur "Login failed"
Vérifiez vos credentials MediaWiki dans `.env`. Le format attendu pour un bot:
- Username: `VotreNom@NomDuBot`
- Password: Token généré depuis Special:BotPasswords

### Page déjà traduite (skipped)
C'est normal ! L'outil vérifie les `langlinks` existants et ignore les pages déjà traduites.

## Commandes utiles

```bash
# Tests rapides
python tests/test_smoke.py

# Vérifier la config
python scripts/check_config.py

# Compter les pages dans un fichier
grep -v "^#" data/my_pages.txt | grep -v "^$" | wc -l

# Voir les dernières traductions
tail -n 10 logs/translated_log.csv
```

## Prochaines étapes

Une fois les bases maîtrisées, vous pouvez:
1. Ajuster les prompts dans `openai_client.py` pour affiner les traductions
2. Modifier `namespace_mapping.py` pour d'autres paires de langues
3. Augmenter `MAX_TOKENS_PER_CHUNK` dans `.env` pour les pages courtes (économie d'API calls)
4. Contribuer au parsing Wikitext avancé dans `wikitext_parser.py`

Bon courage ! 🚀
