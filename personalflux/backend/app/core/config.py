from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "PersonaFlux"
    api_v1_prefix: str = "/api/v1"
    database_url: str          # required: the app refuses to start without it
    jwt_secret_key: str        # required: generate a long random value
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    # A rotated token presented again within this many seconds is treated as a
    # benign race (two tabs refreshing at once), not as theft.
    refresh_reuse_grace_seconds: int = 10
    cors_origins: str = "http://localhost:5173"
    model_artifact_dir: str = "../ml/artifacts"
    # How often a worker checks whether the serving model changed (seconds).
    model_poll_seconds: int = 10
    enable_model_poller: bool = True
    log_level: str = "INFO"
    rate_limit_enabled: bool = True
    max_request_bytes: int = 1_000_000
    # Database pooling. Sized for a single small instance; raise with the instance.
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 1800
    db_pool_timeout_seconds: int = 30
    db_statement_timeout_ms: int = 15000
    # Optional: a tarball the container fetches at boot so the ML artefact is
    # present in environments that do not carry it in the image.
    model_artifact_url: str | None = None
    # Real affiliate catalogue (eBay Browse). Empty values make the importer refuse.
    ebay_client_id: str | None = None
    ebay_client_secret: str | None = None
    ebay_marketplace_id: str = "EBAY_US"
    ebay_oauth_scope: str = "https://api.ebay.com/oauth/api_scope"
    affiliate_campaign_id: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("jwt_secret_key")
    @classmethod
    def _secret_long_enough(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
