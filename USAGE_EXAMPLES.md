# Exemples d'utilisation de gpt_wiki_translator

## Cas d'usage courants

### 1. Tester une seule page en mode simulation (dry-run)
```bash
./translate.sh \
  --page "https://fr.dev.tripleperformance.ag/wiki/Blé" \
  --target-lang en \
  --dry-run
```
**Effet**: Récupère la page, la traduit avec OpenAI, affiche les résultats, mais ne publie rien.

### 2. Traduire une seule page pour de vrai
```bash
./translate.sh \
  --page "https://fr.dev.tripleperformance.ag/wiki/Blé" \
  --target-lang en
```
**Effet**: Traduit et publie sur `en.dev.tripleperformance.ag/wiki/Wheat`, ajoute le lien interwiki sur la page source.

### 3. Retraduire une page qui existe déjà
```bash
./translate.sh \
  --page "https://fr.dev.tripleperformance.ag/wiki/Blé" \
  --target-lang en \
  --force
```
**Effet**: Ignore la vérification d'existence et retraduit/republie la page même si elle existe déjà.

### 4. Traduire un lot de pages depuis un fichier
```bash
./translate.sh \
  --input data/pages_cereales.txt \
  --target-lang en
```
**Contenu de `data/pages_cereales.txt`**:
```
https://fr.dev.tripleperformance.ag/wiki/Blé
https://fr.dev.tripleperformance.ag/wiki/Maïs
https://fr.dev.tripleperformance.ag/wiki/Orge
```

### 5. Test dry-run sur un lot avec forçage
```bash
./translate.sh \
  --input data/pages_a_revoir.txt \
  --target-lang en \
  --force \
  --dry-run
```
**Effet**: Simule la retraduction de toutes les pages du fichier, même celles déjà traduites.

## Exemples avec titres simples (sans URL)

Si `MEDIAWIKI_API_ENDPOINT=https://fr.dev.tripleperformance.ag/api.php` dans `.env`:

### Traduire une page par son titre
```bash
./translate.sh --page "Blé" --target-lang en --dry-run
```

### Traduire un lot de titres
Fichier `data/titres_simples.txt`:
```
Blé
Maïs
Orge
```

```bash
./translate.sh --input data/titres_simples.txt --target-lang en
```

## Environnements mixtes

Vous pouvez mélanger prod et dev dans le même fichier:

`data/mixed_env.txt`:
```
https://fr.tripleperformance.ag/wiki/Page_Prod_1
https://fr.dev.tripleperformance.ag/wiki/Page_Dev_1
https://fr.tripleperformance.ag/wiki/Page_Prod_2
```

```bash
./translate.sh --input data/mixed_env.txt --target-lang en
```

**Résultat**:
- `Page_Prod_1` → publié sur `en.tripleperformance.ag` (prod)
- `Page_Dev_1` → publié sur `en.dev.tripleperformance.ag` (dev)
- `Page_Prod_2` → publié sur `en.tripleperformance.ag` (prod)

## Scénarios de débogage

### Tester les paramètres sans traduction
```bash
./translate.sh --page "Test" --target-lang en --dry-run
# Vérifier les logs pour voir si les endpoints sont corrects
```

### Retraduire après avoir modifié les prompts
```bash
./translate.sh --page "Page_Test" --target-lang en --force --dry-run
# Comparer l'ancienne et la nouvelle traduction
```

### Batch translation avec monitoring
```bash
./translate.sh --input data/large_batch.txt --target-lang en 2>&1 | tee translation.log
# Sauvegarder les logs dans un fichier pour analyse
```

## Notes importantes

1. **Dry-run first**: Toujours tester avec `--dry-run` avant de traduire pour de vrai
2. **Force avec précaution**: `--force` écrasera les traductions existantes
3. **Logs**: Consultez `logs/translated_log.csv` pour l'historique complet
4. **Environnements**: Le script détecte automatiquement prod vs dev depuis l'URL
5. **Coûts**: Chaque traduction consomme des tokens OpenAI (surveillez votre usage)
