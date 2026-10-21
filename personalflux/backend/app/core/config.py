from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def env_file_paths(here: Path) -> tuple[str, ...]:
    """The dotenv files to read, lowest priority first.

    `backend/.env` holds a developer's own overrides. `.env.local` at the
    repository root is the file `neon init` and `neon deploy` write, so it wins
    when both exist: one source of truth for the provisioned database rather than
    a copy pasted into two places.

    Paths are resolved from this file rather than from the working directory,
    because the API is started from `backend/` locally and from `/code` in the
    container, while the repository root is a different number of levels up in
    each. A layout too shallow to have a parent at that depth (the image) is
    skipped rather than raising.
    """
    paths: list[str] = []
    for depth, name in ((2, ".env"), (4, ".env.local")):
        try:
            candidate = here.parents[depth] / name
        except IndexError:
            continue
        if candidate.is_file():
            paths.append(str(candidate))
    return tuple(paths) or (".env",)


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "PersonaFlux"
    api_v1_prefix: str = "/api/v1"
    database_url: str          # required: the app refuses to start without it
    # Neon publishes a direct connection beside the pooled one. Migrations want
    # the direct one; see migration_database_url.
    database_url_unpooled: str | None = None
    jwt_secret_key: str        # required: generate a long random value
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    # A rotated token presented again within this many seconds is treated as a
    # benign race (two tabs refreshing at once), not as theft.
    refresh_reuse_grace_seconds: int = 10
    # "strict" whenever the storefront and API share a registrable domain. A
    # cross-site pair (a *.vercel.app storefront calling a *.run.app API) needs
    # "none", or the browser never sends the refresh cookie and a reload signs the
    # visitor out; "none" is only accepted by browsers on a Secure cookie.
    refresh_cookie_samesite: str = "strict"
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

    model_config = SettingsConfigDict(
        env_file=env_file_paths(Path(__file__).resolve()), extra="ignore"
    )

    @field_validator("database_url", "database_url_unpooled")
    @classmethod
    def _psycopg_driver(cls, v: str | None) -> str | None:
        """Name psycopg 3 explicitly in a plain Postgres URL.

        Hosts hand out `postgresql://…` (Neon does, and so does every Heroku-era
        example). SQLAlchemy reads that as "use psycopg2", which is not installed
        here, so the first query would fail with an import error. Rewriting the
        scheme is what lets a copied connection string work unchanged.
        """
        if v is None:
            return v
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def _secret_long_enough(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("refresh_cookie_samesite")
    @classmethod
    def _known_samesite(cls, v: str) -> str:
        value = v.strip().lower()
        if value not in {"strict", "lax", "none"}:
            raise ValueError("REFRESH_COOKIE_SAMESITE must be strict, lax or none")
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def connection_url(self) -> str:
        """The connection this process uses, for both queries and migrations.

        Neon publishes two endpoints: a pooler for short-lived and serverless
        clients, and a direct connection for long-running ones. This is a
        long-running server with a small pool, and the pooler rejects the startup
        parameter that carries the statement timeout ("unsupported startup
        parameter in options"), so the direct endpoint is preferred when the host
        offers one. Hosts that publish a single URL fall back to it, and the
        engine stays usable behind a pooler either way.

        The direct URL only counts when the configured URL is the pooler beside
        it. Otherwise a stale `.env.local` would silently redirect a database
        someone chose deliberately — a test run, or a machine pointed at staging
        for the afternoon — which is the kind of mix-up that truncates the wrong
        database.
        """
        if self.database_url_unpooled and "-pooler" in self.database_url:
            return self.database_url_unpooled
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
