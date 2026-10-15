"""Safe argument construction for PostgreSQL logical backups."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit


def postgres_dump_invocation(database_url: str, backup_path: str) -> tuple[list[str], dict[str, str]]:
    """Build a shell-free pg_dump invocation and isolated credential environment."""
    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg2"}:
        raise ValueError("Database backup URL must use PostgreSQL.")
    if not parsed.hostname or not parsed.path.strip("/"):
        raise ValueError("PostgreSQL backup URL must include a host and database name.")

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("PostgreSQL backup URL contains an invalid port.") from exc

    username = unquote(parsed.username or "")
    if not username:
        raise ValueError("PostgreSQL backup URL must include a username.")
    database = unquote(parsed.path.lstrip("/").split("/", 1)[0])
    if not database:
        raise ValueError("PostgreSQL backup URL must include a database name.")

    command = [
        "pg_dump",
        "--no-password",
        "--host", parsed.hostname,
        "--username", username,
        "--dbname", database,
        "--file", str(Path(backup_path)),
    ]
    if port is not None:
        command.extend(["--port", str(port)])

    environment: dict[str, str] = {}
    if parsed.password is not None:
        environment["PGPASSWORD"] = unquote(parsed.password)

    # Keep PostgreSQL TLS and connection options from the original URL.
    query_env = {
        "sslmode": "PGSSLMODE",
        "sslrootcert": "PGSSLROOTCERT",
        "sslcert": "PGSSLCERT",
        "sslkey": "PGSSLKEY",
        "connect_timeout": "PGCONNECT_TIMEOUT",
        "application_name": "PGAPPNAME",
        "options": "PGOPTIONS",
    }
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key not in query_env:
            raise ValueError(f"Unsupported PostgreSQL backup URL parameter: {key}")
        environment[query_env[key]] = value
    return command, environment
