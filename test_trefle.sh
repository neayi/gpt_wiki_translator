#!/usr/bin/env bash
# Quick test script for Trèfle page translation
# Usage: ./test_trefle.sh [--force] [--no-dry-run]

cd "$(dirname "$0")"

ARGS="--page https://fr.dev.tripleperformance.ag/wiki/Tr%C3%A8fle --target-lang en --force"

# Add --dry-run by default unless --no-dry-run is passed
if [[ "$*" != *"--no-dry-run"* ]]; then
    ARGS="$ARGS --dry-run"
    echo "ℹ️  Running in DRY-RUN mode (no changes will be published)"
    echo "   Use --no-dry-run to actually publish the translation"
    echo ""
fi

# Pass through other arguments
for arg in "$@"; do
    if [[ "$arg" != "--no-dry-run" ]]; then
        ARGS="$ARGS $arg"
    fi
done

echo "🔍 Testing translation of: Trèfle (fr) → Clover (en)"
echo "📍 Source: https://fr.dev.tripleperformance.ag/wiki/Trèfle"
echo "📍 Target: https://en.dev.tripleperformance.ag/wiki/Trèfle"
echo ""
echo "Command: ./translate.sh $ARGS"
echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

./translate.sh $ARGS

echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""
echo "✅ Translation complete! Check logs/translated_log.csv for results"
