"""The psycopg arguments we hand to the engine, checked without a database.

These two settings are the difference between a hosted Postgres that works and
one that fails intermittently: the statement timeout, and disabling prepared
statements when the URL points at a PgBouncer pooler.
"""
from app.db.session import connect_args_for


def test_a_postgres_url_gets_the_statement_timeout():
    args = connect_args_for("postgresql+psycopg://u:p@host/db", 15000)
    assert args == {"options": "-c statement_timeout=15000"}


def test_a_pooled_url_also_turns_prepared_statements_off():
    # Neon's pooler endpoint is the case this exists for.
    url = "postgresql+psycopg://u:p@ep-cool-1-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    args = connect_args_for(url, 15000)
    assert args["prepare_threshold"] is None
    assert args["options"] == "-c statement_timeout=15000"


def test_a_direct_url_keeps_prepared_statements():
    url = "postgresql+psycopg://u:p@ep-cool-1.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    assert "prepare_threshold" not in connect_args_for(url, 15000)


def test_a_sqlite_url_gets_no_postgres_arguments():
    # Tests and throwaway runs use SQLite; none of these options apply there.
    assert connect_args_for("sqlite:///./test.db", 15000) == {}
