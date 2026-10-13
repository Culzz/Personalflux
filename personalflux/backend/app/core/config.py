from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "PersonaFlux"
    api_v1_prefix: str = "/api/v1"
    database_url: str  # required: the app refuses to start without it
    cors_origins: str = "http://localhost:5173"
    model_artifact_dir: str = "../ml/artifacts"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()