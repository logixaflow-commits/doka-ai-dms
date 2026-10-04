"""Get Supabase connection string from Project Settings > Database > URI.

Run from web-platform/backend with TEST_DATABASE_URL set:
    pytest tests/integration/test_db_auth.py -v
"""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.local_security import decode_local_token


def test_wrong_password_rejected():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL not set")

    bad_url = make_url(database_url).set(password="wrong_password_xyz")
    engine = create_engine(bad_url)
    try:
        with pytest.raises(OperationalError):
            engine.connect()
    finally:
        engine.dispose()


def test_app_user_cannot_drop_table(db_engine):
    with pytest.raises(SQLAlchemyError):
        with db_engine.begin() as connection:
            connection.execute(text("DROP TABLE doka_nonexistent_auth_boundary_test"))


def test_app_user_cannot_create_role(db_engine):
    with pytest.raises(SQLAlchemyError):
        with db_engine.begin() as connection:
            connection.execute(text("CREATE ROLE doka_forbidden_test_role"))


def test_invalid_token_rejected(db_engine):
    assert decode_local_token("not-a-valid-token") is None
