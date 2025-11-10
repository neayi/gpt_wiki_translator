# Rapport de test - Publication de la page Trèfle → Clover

## ✅ Ce qui fonctionne

### 1. Pipeline complet
- ✅ Récupération du wikitext source (Trèfle)
- ✅ Traduction du titre : "Trèfle" → "Clover"
- ✅ Traduction du contenu avec OpenAI
- ✅ Publication sur le wiki anglais (https://en.dev.tripleperformance.ag/wiki/Clover)
- ✅ Ajout du lien interwiki sur la page source : `[[:en:Clover]]`
- ✅ Log CSV avec date et statut
- ✅ Gestion SSL automatique pour environnement .dev

### 2. Authentification et permissions
- ✅ Login réussi avec les credentials bot
- ✅ Token CSRF obtenu et utilisé
- ✅ Édition de pages autorisée

### 3. Détection et gestion
- ✅ Détection de traductions existantes (langlinks)
- ✅ Flag `--force` pour retraduction
- ✅ Mode `--dry-run` pour tests
- ✅ Barre de progression

## ⚠️ Problèmes identifiés (qualité de traduction)

### 1. Espaces manquants dans les liens
**Observé** :
```
The[[:Catégorie:Trèfles|trèfles]]are herbaceous plants
```

**Attendu** :
```
The [[:Catégorie:Trèfles|trèfles]] are herbaceous plants
```

**Cause** : Le parser protège les wikilinks entièrement, mais l'IA ne gère pas correctement les espaces avant/après.

### 2. Templates partiellement traduits
**Observé** :
```
{{Culture
| Nom = Trèfle
| Icone = Trèfle.png
```

**Attendu** :
- Noms de paramètres non traduits : `Nom` devrait rester `Nom` (ou le template entier devrait être préservé tel quel)
- Valeurs comme "Trèfle" dans les paramètres ne devraient pas être traduites si c'est un nom de fichier

**Cause** : Segmentation trop grossière - les templates sont marqués comme "protected" mais leurs paramètres peuvent être partiellement exposés.

### 3. Catégories et namespaces mixtes
**Observé** :
```
[[:Catégorie:Trèfles|trèfles]]
```

**Attendu** :
```
[[:Category:Clovers|clovers]]
```

**Cause** : Le mapping de namespace n'est appliqué qu'au titre de page, pas aux liens internes dans le contenu.

### 4. Contenu ajouté par l'IA
Le validateur OpenAI rapporte : "Additional unrelated content (Infobox person and biography of John Doe) inserted"

**Cause** : L'IA peut parfois "halluciner" et ajouter du contenu qui n'existe pas dans la source.

## 🔧 Actions correctives prioritaires

### Priorité 1 : Parser Wikitext avancé
1. **Segmentation fine des templates**
   - Protéger les noms de templates
   - Protéger les noms de paramètres
   - Ne traduire QUE les valeurs textuelles (pas les noms de fichiers)

2. **Gestion des liens internes**
   - Détecter `[[...]]` 
   - Mapper les namespaces dans les liens : `[[Catégorie:X]]` → `[[Category:X]]`
   - Préserver les espaces autour des liens

3. **Gestion des fichiers/images**
   - Pattern : `[[Fichier:nom|params|légende]]`
   - Ne PAS traduire : `nom` (nom du fichier)
   - NE PAS traduire : paramètres de taille (`500px`, `thumb`, etc.)
   - TRADUIRE : légende uniquement

### Priorité 2 : Amélioration des prompts OpenAI
1. **Prompt de traduction plus strict**
   ```
   - DO NOT add any content not present in the source
   - DO NOT remove any content from the source
   - Preserve ALL whitespace around wiki syntax
   - DO NOT translate template names or parameter names
   - DO NOT translate file names
   ```

2. **Validation post-traduction renforcée**
   - Comparer la structure AST avant/après
   - Vérifier que tous les templates sources existent dans la cible
   - Vérifier que tous les fichiers sources existent dans la cible
   - Rejeter et recommencer si validation échoue

### Priorité 3 : Chunking intelligent
- Découper par sections (`== Titre ==`)
- Respecter les limites de tokens
- Maintenir le contexte entre chunks

## 📊 Résultats du test

| Critère | Statut | Note |
|---------|--------|------|
| Pipeline technique | ✅ | 100% |
| Authentification | ✅ | 100% |
| Publication | ✅ | 100% |
| Qualité traduction | ⚠️ | 40% |
| Préservation structure | ⚠️ | 30% |

## 🎯 Prochaines étapes

1. **Court terme** : Améliorer le parser wikitext (priorité 1)
2. **Moyen terme** : Renforcer la validation et les prompts (priorité 2)
3. **Long terme** : Implémenter le chunking (priorité 3)

## 📝 Commandes de vérification

```bash
# Voir la page anglaise publiée
curl -k "https://en.dev.tripleperformance.ag/wiki/Clover"

# Vérifier le lien interwiki sur la page française
curl -k -s "https://fr.dev.tripleperformance.ag/api.php?action=query&titles=Tr%C3%A8fle&prop=revisions&rvprop=content&rvslots=main&format=json" | grep "en:Clover"

# Voir les logs
python scripts/show_logs.py
```
