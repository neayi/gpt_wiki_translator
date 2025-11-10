#!/usr/bin/env python3
"""Démonstration du système de chunking par sections."""
from gpt_wiki_translator.chunking import create_chunks, get_chunk_stats

# Exemple de wikitext avec plusieurs sections
sample_wikitext = """{{Culture
| Nom = Trèfle
| Icone = Trèfle.png
}}

Le '''trèfle''' est une plante légumineuse cultivée.

== Description ==

Le trèfle est caractérisé par ses feuilles composées de trois folioles.

=== Variétés ===

Il existe plusieurs variétés de trèfle:
* Trèfle blanc
* Trèfle violet
* Trèfle incarnat

== Culture ==

Le trèfle se cultive facilement dans les prairies.

=== Semis ===

Le semis s'effectue au printemps ou à l'automne.

=== Entretien ===

L'entretien est minimal.

== Utilisations ==

Le trèfle est utilisé comme:
* Fourrage pour le bétail
* Engrais vert
* Plante mellifère

== Voir aussi ==

* [[Légumineuses]]
* [[Prairie]]
"""

def main():
    print("=" * 70)
    print("DÉMONSTRATION DU CHUNKING PAR SECTIONS")
    print("=" * 70)
    
    # Test avec différentes tailles maximales
    for max_tokens in [100, 300, 1000, 5000]:
        print(f"\n📊 Max tokens: {max_tokens}")
        print("-" * 70)
        
        chunks = create_chunks(sample_wikitext, max_tokens=max_tokens)
        stats = get_chunk_stats(chunks)
        
        print(f"Nombre de chunks: {stats['count']}")
        print(f"Tokens estimés: min={stats['min_tokens']}, max={stats['max_tokens']}, avg={stats['avg_tokens']}")
        print(f"Total caractères: {stats['total_chars']}")
        
        print("\n📝 Aperçu des chunks:")
        for i, chunk in enumerate(chunks, 1):
            preview = chunk[:80].replace('\n', ' ')
            if len(chunk) > 80:
                preview += '...'
            print(f"  Chunk {i} ({len(chunk)} chars, ~{len(chunk)//3} tokens): {preview}")

if __name__ == '__main__':
    main()
