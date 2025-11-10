import logging
from pathlib import Path
from .config import get_settings

_LOGGER: logging.Logger | None = None

def get_logger() -> logging.Logger:
    global _LOGGER
    if _LOGGER:
        return _LOGGER
    settings = get_settings()
    logger = logging.getLogger('gpt_wiki_translator')
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_path = Path(settings.log_csv_path).parent
    log_path.mkdir(parents=True, exist_ok=True)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    _LOGGER = logger
    return logger
