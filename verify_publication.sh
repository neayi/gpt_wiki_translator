#!/usr/bin/env bash
# Verify that the Clover page was properly published and interwiki link added

echo "🔍 Vérification de la publication de Clover..."
echo ""

# Check English page exists
echo "1️⃣ Vérification existence de la page anglaise..."
RESPONSE=$(curl -k -s "https://en.dev.tripleperformance.ag/api.php?action=query&titles=Clover&format=json")
if echo "$RESPONSE" | grep -q '"pageid"'; then
    PAGE_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(list(data['query']['pages'].keys())[0])")
    echo "   ✅ Page 'Clover' existe (ID: $PAGE_ID)"
else
    echo "   ❌ Page 'Clover' n'existe pas"
    exit 1
fi

# Check interwiki link on French page
echo ""
echo "2️⃣ Vérification du lien interwiki sur la page française..."
FR_CONTENT=$(curl -k -s "https://fr.dev.tripleperformance.ag/api.php?action=query&titles=Tr%C3%A8fle&prop=revisions&rvprop=content&rvslots=main&format=json" | python3 -c "import sys, json; data=json.load(sys.stdin); page=list(data['query']['pages'].values())[0]; print(page['revisions'][0]['slots']['main']['*'])")

if echo "$FR_CONTENT" | grep -q "\[\[en:Clover\]\]"; then
    echo "   ✅ Lien interwiki [[en:Clover]] présent sur page FR"
else
    echo "   ❌ Lien interwiki manquant sur page FR"
    exit 1
fi

# Check interwiki link on English page (back to French)
echo ""
echo "3️⃣ Vérification du lien interwiki sur la page anglaise..."
EN_CONTENT=$(curl -k -s "https://en.dev.tripleperformance.ag/api.php?action=query&titles=Clover&prop=revisions&rvprop=content&rvslots=main&format=json" | python3 -c "import sys, json; data=json.load(sys.stdin); page=list(data['query']['pages'].values())[0]; print(page['revisions'][0]['slots']['main']['*'])")

if echo "$EN_CONTENT" | grep -q "\[\[fr:Trèfle\]\]"; then
    echo "   ✅ Lien interwiki [[fr:Trèfle]] présent sur page EN"
else
    echo "   ⚠️  Lien interwiki manquant sur page EN"
fi

# Check log entry
echo ""
echo "4️⃣ Vérification du log CSV..."
if [ -f "logs/translated_log.csv" ]; then
    LAST_ENTRY=$(tail -1 logs/translated_log.csv)
    if echo "$LAST_ENTRY" | grep -q "Trèfle,Clover"; then
        echo "   ✅ Entrée de log trouvée"
        echo "   📊 Dernière entrée: $(echo $LAST_ENTRY | cut -d',' -f1-5)"
    else
        echo "   ⚠️  Log existe mais dernière entrée n'est pas Trèfle→Clover"
    fi
else
    echo "   ❌ Fichier de log manquant"
    exit 1
fi

# Show English page preview
echo ""
echo "5️⃣ Aperçu du contenu anglais (100 premiers caractères)..."
PREVIEW=$(curl -k -s "https://en.dev.tripleperformance.ag/api.php?action=query&titles=Clover&prop=revisions&rvprop=content&rvslots=main&format=json" | python3 -c "import sys, json; data=json.load(sys.stdin); page=list(data['query']['pages'].values())[0]; content=page['revisions'][0]['slots']['main']['*']; print(content[:200])")
echo "   📄 $PREVIEW..."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Toutes les vérifications ont réussi!"
echo ""
echo "🌐 URLs:"
echo "   Source (FR): https://fr.dev.tripleperformance.ag/wiki/Trèfle"
echo "   Target (EN): https://en.dev.tripleperformance.ag/wiki/Clover"
echo ""
