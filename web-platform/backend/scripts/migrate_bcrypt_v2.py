"""Add the password hash version marker without changing existing hashes."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app.core.database import engine


def migrate() -> int:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        raise RuntimeError("Cannot migrate bcrypt hashes: users table does not exist.")

    columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as connection:
        if "password_version" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE users ADD COLUMN "
                    "password_version INTEGER NOT NULL DEFAULT 1"
                )
            )
        count = connection.execute(
            text("SELECT COUNT(*) FROM users WHERE password_version = 1")
        ).scalar_one()

    return count


if __name__ == "__main__":
    print(f"Rows still on password version 1: {migrate()}")
