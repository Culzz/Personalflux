"""How settings are found and how a hosted Postgres URL is translated.

`neon deploy` writes `.env.local` at the repository root and hands over a plain
`postgresql://` URL, so these two pieces of plumbing decide whether the API can
start at all. They are pure functions and a validator, so none of this needs a
database.
"""
import os
from pathlib import Path

import pytest

from app.core.config import Settings, env_file_paths

SECRET = "x" * 40


def _settings(**overrides) -> Settings:
    # _env_file=None keeps the machine's own dotenv files out of the test.
    values = {"jwt_secret_key": SECRET, **overrides}
    return Settings(_env_file=None, **values)


def test_the_checked_out_layout_reads_the_backend_env_then_the_neon_one(tmp_path):
    root = tmp_path / "repo"
    backend = root / "personalflux" / "backend"
    here = backend / "app" / "core" / "config.py"
    here.parent.mkdir(parents=True)
    here.write_text("", encoding="utf-8")
    (backend / ".env").write_text("DATABASE_URL=local\n", encoding="utf-8")
    (root / ".env.local").write_text("DATABASE_URL=neon\n", encoding="utf-8")

    paths = env_file_paths(here)

    # Lowest priority first: the Neon file is last, so it wins.
    assert paths == (str(backend / ".env"), str(root / ".env.local"))


def test_a_layout_without_any_dotenv_file_falls_back_to_the_working_directory(tmp_path):
    # The container is /code/app/core/config.py: no repository root above it.
    here = tmp_path / "code" / "app" / "core" / "config.py"
    here.parent.mkdir(parents=True)
    here.write_text("", encoding="utf-8")

    assert env_file_paths(here) == (".env",)


@pytest.mark.parametrize(
    "given,expected",
    [
        ("postgresql://u:p@h/db?sslmode=require", "postgresql+psycopg://u:p@h/db?sslmode=require"),
        ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        # Already explicit: leave it alone.
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:///./test.db", "sqlite:///./test.db"),
    ],
)
def test_a_hosted_postgres_url_selects_psycopg3(given, expected):
    assert _settings(database_url=given).database_url == expected


def test_the_direct_url_is_translated_too():
    direct = "postgresql://u:p@ep-1.eu-central-1.aws.neon.tech/db"
    assert _settings(database_url=direct, database_url_unpooled=direct).database_url_unpooled == (
        "postgresql+psycopg://u:p@ep-1.eu-central-1.aws.neon.tech/db"
    )


def test_the_direct_connection_is_preferred_when_published():
    pooled = "postgresql+psycopg://u:p@ep-1-pooler.eu-central-1.aws.neon.tech/db"
    direct = "postgresql+psycopg://u:p@ep-1.eu-central-1.aws.neon.tech/db"
    s = _settings(database_url=pooled, database_url_unpooled=direct)
    assert s.database_url == pooled          # the URL Neon hands out
    assert s.connection_url == direct        # what this process opens


def test_a_stale_direct_url_does_not_hijack_another_database():
    # A .env.local left over from a Neon project, beside a deliberately chosen
    # DATABASE_URL: the choice wins.
    chosen = "postgresql+psycopg://u:p@localhost:5432/personalflux_test"
    stale = "postgresql+psycopg://u:p@ep-1.eu-central-1.aws.neon.tech/neondb"
    assert _settings(database_url=chosen, database_url_unpooled=stale).connection_url == chosen


def test_a_single_url_host_still_has_a_connection():
    url = "postgresql+psycopg://u:p@localhost:5432/personalflux"
    assert _settings(database_url=url).connection_url == url


def test_the_engine_uses_the_database_the_suite_selected():
    # conftest pins DATABASE_URL to the test database while .env.local may hold a
    # hosted pair. Every test truncates tables afterwards, so opening anything but
    # that pin would delete someone's data.
    from app.core.config import settings

    assert settings.connection_url == os.environ["DATABASE_URL"]


def test_a_hostile_secret_is_still_refused():
    with pytest.raises(ValueError):
        _settings(database_url="sqlite://", jwt_secret_key="short")


@pytest.mark.parametrize(
    "given,expected", [("Strict", "strict"), (" lax ", "lax"), ("NONE", "none")]
)
def test_the_refresh_cookie_policy_is_normalised(given, expected):
    assert _settings(database_url="sqlite://", refresh_cookie_samesite=given).refresh_cookie_samesite == expected


def test_an_unknown_refresh_cookie_policy_is_refused():
    with pytest.raises(ValueError):
        _settings(database_url="sqlite://", refresh_cookie_samesite="sometimes")
