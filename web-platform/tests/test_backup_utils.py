from app.core.backup_utils import postgres_dump_invocation


def test_postgres_dump_parses_encoded_credentials_and_ipv6_without_shell():
    command, environment = postgres_dump_invocation(
        "postgresql+psycopg2://backup%40user:p%40ss%3Aword@[2001:db8::1]:5544/doka%2Farchive",
        "/safe/backups/doka.sql",
    )

    assert command == [
        "pg_dump", "--no-password",
        "--host", "2001:db8::1",
        "--username", "backup@user",
        "--dbname", "doka/archive",
        "--file", "/safe/backups/doka.sql",
        "--port", "5544",
    ]
    assert environment == {"PGPASSWORD": "p@ss:word"}


def test_postgres_dump_does_not_add_empty_password():
    command, environment = postgres_dump_invocation(
        "postgresql://backup@db.example.test:5432/doka",
        "/tmp/doka.sql",
    )
    assert "--password" not in command
    assert environment == {}


def test_postgres_dump_rejects_missing_host_database_and_invalid_port():
    import pytest

    for value in (
        "postgresql:///doka",
        "postgresql://backup@db.example.test/",
        "postgresql://backup@db.example.test:99999/doka",
        "sqlite:///doka.db",
    ):
        with pytest.raises(ValueError):
            postgres_dump_invocation(value, "/tmp/doka.sql")
