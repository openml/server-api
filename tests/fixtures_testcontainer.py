import contextlib
import os
import re
from collections.abc import Generator, Iterator

import pytest
import sqlalchemy
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine
from testcontainers.mysql import LogMessageWaitStrategy, MySqlContainer

from main import create_api
from routers.dependencies import expdb_connection, userdb_connection

load_dotenv()


@pytest.fixture(scope="session", autouse=True)
def override_testcontainers_connect() -> None:
    """
    Override MySqlContainer._connect once per test session.
    Applied automatically everywhere.
    """

    def _connect(self: MySqlContainer) -> None:
        wait_strategy = LogMessageWaitStrategy(
            re.compile(
                r".*: ready for connections",
                flags=re.DOTALL | re.MULTILINE,
            )
        )
        wait_strategy.wait_until_ready(self)

    MySqlContainer._connect = _connect  # noqa: SLF001


@pytest.fixture(scope="session")
def mysql_container() -> MySqlContainer:
    container = MySqlContainer(
        os.environ.get(
            "OPENML_DATABASES_OPENML_URL",
            "openml/test-database:v0.1.20260204",
        ),
        username=os.environ.get("OPENML_DATABASES_OPENML_USERNAME", ""),
        password=os.environ.get("OPENML_DATABASES_OPENML_PASSWORD", ""),
        dbname="openml_expdb",
    )

    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture
def expdb_test(mysql_container: MySqlContainer) -> Connection:
    url = mysql_container.get_connection_url().replace("mysql://", "mysql+pymysql://")
    engine = sqlalchemy.create_engine(url)

    with engine.begin() as connection:  # This starts a transaction
        try:
            yield connection
        finally:
            connection.rollback()  # Rollback ALL test changes


@contextlib.contextmanager
def automatic_rollback(engine: Engine) -> Iterator[Connection]:
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        if transaction.is_active:
            transaction.rollback()


@pytest.fixture
def py_api(expdb_test: Connection, user_test: Connection) -> Generator[TestClient, None, None]:
    app = create_api()
    # We use the lambda definitions because fixtures may not be called directly.
    app.dependency_overrides[expdb_connection] = lambda: expdb_test
    app.dependency_overrides[userdb_connection] = lambda: user_test

    client = TestClient(app)
    yield client
    client.close()


@pytest.fixture
def user_test(mysql_container: MySqlContainer) -> Connection:
    """Get a connection to the user database using the testcontainer."""
    url = mysql_container.get_connection_url()
    url = url.replace("mysql://", "mysql+pymysql://")
    url = url.replace("openml_expdb", "openml")

    engine = sqlalchemy.create_engine(url)
    with automatic_rollback(engine) as connection:
        yield connection
