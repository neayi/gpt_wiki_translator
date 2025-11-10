# Test rapide - Page Trèfle

## Nouvelles fonctionnalités ajoutées

### 1. Support SSL flexible pour environnements dev
- **Auto-détection**: La vérification SSL est automatiquement désactivée pour les URLs contenant `.dev.`
- **Option manuelle**: `--no-verify-ssl` pour forcer la désactivation
- Suppression des warnings urllib3 quand SSL est désactivé

### 2. Nouveaux paramètres CLI

#### `--page` : Test sur une seule page
```bash
./translate.sh --page "https://fr.dev.tripleperformance.ag/wiki/Trèfle" --target-lang en --dry-run
```

#### `--force` : Retraduire même si existe
```bash
./translate.sh --page "Trèfle" --target-lang en --force
```

#### `--no-verify-ssl` : Désactiver SSL manuellement
```bash
./translate.sh --page "Test" --target-lang en --no-verify-ssl
```

## Test de la page Trèfle

### Script de test rapide
```bash
./test_trefle.sh                  # Dry-run (par défaut)
./test_trefle.sh --force          # Dry-run avec force
./test_trefle.sh --no-dry-run     # Publication réelle
```

### Test manuel
```bash
# 1. Dry-run (recommandé d'abord)
./translate.sh \
  --page "https://fr.dev.tripleperformance.ag/wiki/Tr%C3%A8fle" \
  --target-lang en \
  --dry-run

# 2. Vérifier les logs
cat logs/translated_log.csv | tail -1

# 3. Si satisfait, publier pour de vrai
./translate.sh \
  --page "https://fr.dev.tripleperformance.ag/wiki/Tr%C3%A8fle" \
  --target-lang en
```

## Résultats attendus

### En mode dry-run
- ✅ Connexion à fr.dev.tripleperformance.ag (SSL désactivé auto)
- ✅ Récupération du wikitext de "Trèfle"
- ✅ Segmentation et traduction avec OpenAI
- ✅ Validation locale
- ✅ Log CSV mis à jour
- ❌ Pas de publication sur en.dev.tripleperformance.ag
- ❌ Pas d'ajout de lien interwiki

### En mode production (sans --dry-run)
- ✅ Tout ce qui précède +
- ✅ Publication sur https://en.dev.tripleperformance.ag/wiki/Trèfle
- ✅ Ajout du lien `[[en:Trèfle]]` dans la page source française

## Vérification post-traduction

```bash
# Voir le dernier log
tail -1 logs/translated_log.csv

# Format attendu:
# Trèfle,Trèfle,fr,en,translated,2025-11-10T...,<issues éventuels>
```

## Debugging

Si erreurs:
1. Vérifier configuration: `python scripts/check_config.py`
2. Vérifier connectivité: `curl -k https://fr.dev.tripleperformance.ag/api.php`
3. Logs détaillés dans la console
4. CSV log: `logs/translated_log.csv`

## Points d'attention actuels

⚠️ **Warnings normaux**:
- "Brace count mismatch": Le parser actuel ne gère pas parfaitement tous les templates imbriqués
- Ces warnings seront réduits avec l'amélioration du parsing Wikitext

✅ **Comportement correct**:
- Auto-désactivation SSL pour .dev.
- Gestion des caractères accentués (Trèfle)
- Dry-run ne modifie rien
- Force permet retraduction
