from __future__ import annotations
from typing import List, Tuple
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from .config import get_settings
from .logging_utils import get_logger

logger = get_logger()

SYSTEM_TRANSLATE = (
    "Tu es un traducteur MediaWiki professionnel. Traduire le texte FR vers la langue cible en conservant strictement: "
    "templates (noms & paramètres non traduits), fichiers/images, fonctions parser, liens internes. "
    "Traduire les namespaces s'ils sont en français (Catégorie -> Category, Fichier -> File, etc.). "
    "Ne JAMAIS ajouter ou supprimer de balises. Retourne du Wikitext strictement formaté."
)

SYSTEM_VALIDATE = (
    "Tu es un validateur. Analyse la traduction fournie et retourne un JSON strict avec les booléens: "
    "{\"preserved_templates\": bool, \"preserved_links\": bool, \"preserved_files\": bool, \"same_brace_count\": bool, \"issues\": [str]}. "
    "Ne retourne rien d'autre."
)

class OpenAIClient:
    def __init__(self):
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def translate_chunk(self, text: str, source_lang: str, target_lang: str) -> str:
        # logger.info('Translating chunk (%d chars)...', len(text))
        completion = self.client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=self.settings.temperature,
            messages=[
                {"role": "system", "content": SYSTEM_TRANSLATE},
                {"role": "user", "content": f"Langue source: {source_lang}\nLangue cible: {target_lang}\n\n{text}"},
            ],
        )
        return completion.choices[0].message.content or ''

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def validate_translation(self, original: str, translated: str) -> str:
        # Could include counts / hints to help validator
        prompt = (
            "Original:\n" + original[:2000] + "\n---\nTraduction:\n" + translated[:2000]
        )
        completion = self.client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_VALIDATE},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content or '{}'
