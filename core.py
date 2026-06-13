import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Cache
    grocery_chain_cache_ttl: int = 3600
    """In seconds"""

    # Retreat
    retreat_email: str
    retreat_password: str


APP_CONFIG = AppConfig()  # ty:ignore[missing-argument]
