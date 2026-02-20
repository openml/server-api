import contextlib
from collections.abc import Iterator

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine

from database.setup import expdb_database, user_database
from main import create_api
from routers.dependencies import expdb_connection, userdb_connection

load_dotenv()


@contextlib.contextmanager
def automatic_rollback(engine: Engine) -> Iterator[Connection]:
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        if transaction.is_active:
            transaction.rollback()


@pytest.fixture
def expdb_test() -> Connection:
    with automatic_rollback(expdb_database()) as connection:
        yield connection


@pytest.fixture
def user_test() -> Connection:
    with automatic_rollback(user_database()) as connection:
        yield connection


@pytest.fixture
def py_api(expdb_test: Connection, user_test: Connection) -> TestClient:
    app = create_api()
    # We use the lambda definitions because fixtures may not be called directly.
    app.dependency_overrides[expdb_connection] = lambda: expdb_test
    app.dependency_overrides[userdb_connection] = lambda: user_test
    return TestClient(app)
