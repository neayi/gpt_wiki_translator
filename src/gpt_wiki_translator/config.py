from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    openai_api_key: str = Field(alias='OPENAI_API_KEY')
    openai_model: str = Field('gpt-4.1-mini', alias='OPENAI_MODEL')
    # Par défaut pour les lignes d'entrée qui ne sont pas des URLs
    mediawiki_api_endpoint: str | None = Field(default=None, alias='MEDIAWIKI_API_ENDPOINT')
    mediawiki_username: str | None = Field(default=None, alias='MEDIAWIKI_USERNAME')
    mediawiki_password: str | None = Field(default=None, alias='MEDIAWIKI_PASSWORD')
    max_tokens_per_chunk: int = Field(1800, alias='MAX_TOKENS_PER_CHUNK')
    temperature: float = Field(0.2, alias='TEMPERATURE')
    log_csv_path: str = Field('logs/translated_log.csv', alias='LOG_CSV_PATH')

    class Config:
        env_file = '.env'
        case_sensitive = True

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
