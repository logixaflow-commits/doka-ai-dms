import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture
def database_url():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL not set")
    return database_url


@pytest.fixture
def db_engine(database_url):
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    except SQLAlchemyError as exc:
        engine.dispose()
        pytest.skip(f"Test database is unreachable: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture
def invalid_password_database_url(database_url):
    url = make_url(database_url)
    return url.set(password="intentionally-wrong-password").render_as_string(
        hide_password=False
    )
