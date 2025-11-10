from __future__ import annotations
from typing import List, Tuple
import mwparserfromhell

# Types
Segment = Tuple[str, str]  # (kind, content) where kind can be 'text' or 'protected'

PROTECTED_NODE_TYPES = (
    mwparserfromhell.nodes.Template,
    mwparserfromhell.nodes.Tag,
    mwparserfromhell.nodes.Comment,
    mwparserfromhell.nodes.Wikilink,
    mwparserfromhell.nodes.ExternalLink,
)

def segment_wikitext(wikitext: str) -> List[Segment]:
    """Découpe le wikitext en segments textuels traduisibles et segments protégés.
    Idée: On parcourt l'AST, on stocke les nodes templates/liens comme 'protected',
    et le texte brut isolé comme 'text'."""
    code = mwparserfromhell.parse(wikitext)
    segments: List[Segment] = []
    for node in code.nodes:
        if isinstance(node, PROTECTED_NODE_TYPES):
            segments.append(('protected', str(node)))
        else:
            # Les autres nodes peuvent contenir du texte (ex: Text, Heading)
            segments.append(('text', str(node)))
    return segments

def merge_translated(segments: List[Segment], translated_texts: List[str]) -> str:
    """Reconstruit le wikitext complet à partir des segments.
    translated_texts correspond 1:1 aux segments de type 'text'."""
    out_parts: List[str] = []
    text_index = 0
    for kind, content in segments:
        if kind == 'protected':
            out_parts.append(content)
        else:
            out_parts.append(translated_texts[text_index])
            text_index += 1
    return ''.join(out_parts)

def count_braces(wikitext: str) -> tuple[int, int]:
    return wikitext.count('{{'), wikitext.count('}}')
