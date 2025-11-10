#!/usr/bin/env bash
# Wrapper script to run gpt_wiki_translator with proper PYTHONPATH
# Usage: ./translate.sh --page "My_Page" --target-lang en --dry-run

cd "$(dirname "$0")"
PYTHONPATH=src exec .venv/bin/python -m gpt_wiki_translator.cli "$@"
