from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase
    supabase_url: str
    supabase_publishable_key: str
    supabase_secret_key: str
    supabase_jwks_url: str
    
    databento_api_key: str | None = None

    # CORS
    allowed_origins: str = "http://localhost:3000/"

    # API
    api_v1_prefix: str = "/api/v1"

    # Feature flags (upgrade seams)
    marketdata_provider: str = "databento"       # yahoo | dxfeed
    indicator_runtime: str = "stub"          # stub | hoox_pyne

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()