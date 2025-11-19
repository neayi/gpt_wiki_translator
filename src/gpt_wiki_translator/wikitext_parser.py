from __future__ import annotations
from typing import List, Tuple, Dict, Any
import mwparserfromhell
import unicodedata

# Types
Segment = Tuple[str, str]  # (kind, content) where kind can be 'text' or 'protected'

PROTECTED_NODE_TYPES = (
    mwparserfromhell.nodes.Template,
    mwparserfromhell.nodes.Tag,
    mwparserfromhell.nodes.Comment,
    mwparserfromhell.nodes.Wikilink,
    mwparserfromhell.nodes.ExternalLink,
)

# Paramètres de templates dont les valeurs ne doivent JAMAIS être traduites
PROTECTED_TEMPLATE_PARAMS = {
    'glyph',
    'icone',
    'bannière',
    'banniere',  # variante sans accent éventuelle
    "photo de l'agriculteur",
    'logo',
    "photo d'illustration",
    'logo organisme',
    'image',
    'class',
    'type de page',
    'frame',
    'query',
}

def _normalize_param_name(name: str) -> str:
    """Normalise un nom de paramètre pour comparaison (minuscule, sans accents, trim)."""
    name = name.strip().lower()
    # Remove diacritics
    name = ''.join(ch for ch in unicodedata.normalize('NFD', name) if unicodedata.category(ch) != 'Mn')
    return name

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


def restore_protected_template_params(original_wikitext: str, translated_wikitext: str) -> str:
    """Restaure dans le wikitext traduit les valeurs des paramètres sensibles qui ne doivent pas
    être modifiées par la traduction.

    Stratégie:
    1. Parse original et collecter (template_index, normalized_param_name) -> valeur originale.
    2. Parse traduit et pour chaque template/param correspondant, replacer la valeur originale.
    On s'appuie sur l'ordre des templates pour limiter ambiguïtés (suffisant dans ce contexte).
    """
    try:
        orig_code = mwparserfromhell.parse(original_wikitext)
        trans_code = mwparserfromhell.parse(translated_wikitext)
    except Exception:
        return translated_wikitext  # en cas de parsing impossible, on ne touche à rien

    # Collecte des valeurs originales
    original_values: Dict[Tuple[int, str], str] = {}
    for idx, node in enumerate(orig_code.filter_templates()):
        if not isinstance(node, mwparserfromhell.nodes.Template):
            continue
        for param in node.params:
            norm = _normalize_param_name(str(param.name))
            if norm in PROTECTED_TEMPLATE_PARAMS:
                original_values[(idx, norm)] = str(param.value)

    if not original_values:
        return translated_wikitext  # rien à restaurer

    # Remplacement dans la version traduite
    for idx, node in enumerate(trans_code.filter_templates()):
        if not isinstance(node, mwparserfromhell.nodes.Template):
            continue
        for param in node.params:
            norm = _normalize_param_name(str(param.name))
            key = (idx, norm)
            if key in original_values:
                # Remplacer la valeur du paramètre si différente
                try:
                    if str(param.value) != original_values[key]:
                        param.value = original_values[key]
                except Exception:
                    continue

    return str(trans_code)

def extract_json_template_params(wikitext: str) -> List[str]:
    """Return list of raw values for parameters named 'json' in any template.
    The value usually looks like 'Page/Subpage.json'."""
    try:
        code = mwparserfromhell.parse(wikitext)
    except Exception:
        return []
    results: List[str] = []
    for tpl in code.filter_templates():
        if not isinstance(tpl, mwparserfromhell.nodes.Template):
            continue
        for param in tpl.params:
            norm = _normalize_param_name(str(param.name))
            if norm == 'json':
                results.append(str(param.value).strip())
    return results

def mask_templates_for_translation(wikitext: str) -> Tuple[str, Dict[str, str]]:
    """Replace template names and parameter keys with placeholders to prevent their translation.
    Returns (masked_wikitext, placeholder_mapping).

    Placeholders use uncommon delimiters to avoid model alterations.
    Template names: ⟪TPL_i⟫
    Parameter keys: ⟪K_i_j⟫
    Values are left intact for translation (unless later restored by protection logic).
    """
    try:
        code = mwparserfromhell.parse(wikitext)
    except Exception:
        return wikitext, {}
    mapping: Dict[str, str] = {}
    output_parts: List[str] = []
    tpl_index = 0
    for node in code.nodes:
        if isinstance(node, mwparserfromhell.nodes.Template):
            tpl_name_placeholder = f'⟪TPL_{tpl_index}⟫'
            mapping[tpl_name_placeholder] = str(node.name)
            param_strings: List[str] = []
            for param_index, param in enumerate(node.params):
                key_placeholder = f'⟪K_{tpl_index}_{param_index}⟫'
                mapping[key_placeholder] = str(param.name)
                # Keep raw value (string) for translation
                param_strings.append(f'{key_placeholder}={param.value}')
            masked = '{{' + tpl_name_placeholder
            if param_strings:
                masked += '|' + ' | '.join(param_strings)
            masked += '}}'
            output_parts.append(masked)
            tpl_index += 1
        else:
            output_parts.append(str(node))
    return ''.join(output_parts), mapping

def restore_masked_templates(masked_translated_wikitext: str, mapping: Dict[str, str]) -> str:
    """Restore original template names and parameter keys from placeholder mapping."""
    restored = masked_translated_wikitext
    # Replace longer placeholders first (order doesn't really matter but deterministic)
    for placeholder in sorted(mapping.keys(), key=lambda x: (-len(x), x)):
        restored = restored.replace(placeholder, mapping[placeholder])
    return restored
