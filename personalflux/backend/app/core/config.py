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
    cors_origins: str = "http://localhost:5173"
    model_artifact_dir: str = "../ml/artifacts"
    log_level: str = "INFO"
    rate_limit_enabled: bool = True
    max_request_bytes: int = 1_000_000

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


settings = Settings()
