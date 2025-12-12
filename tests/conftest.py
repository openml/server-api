import contextlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Any, Generator

import httpx
import pytest
from database.setup import expdb_database, user_database
from fastapi.testclient import TestClient
from main import create_api
from routers.dependencies import expdb_connection, userdb_connection
from sqlalchemy import Connection, Engine

PHP_API_URL = "http://openml-php-rest-api:80/api/v1/json"


class ApiKey(StrEnum):
    ADMIN: str = "AD000000000000000000000000000000"
    REGULAR_USER: str = "00000000000000000000000000000000"
    OWNER_USER: str = "DA1A0000000000000000000000000000"
    INVALID: str = "11111111111111111111111111111111"


@contextlib.contextmanager
def automatic_rollback(engine: Engine) -> Generator[Connection, None, None]:
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture()
def expdb_test() -> Connection:
    with automatic_rollback(expdb_database()) as connection:
        yield connection


@pytest.fixture()
def user_test() -> Connection:
    with automatic_rollback(user_database()) as connection:
        yield connection


@pytest.fixture()
def php_api() -> httpx.Client:
    with httpx.Client(base_url=PHP_API_URL) as client:
        yield client


@pytest.fixture()
def py_api(expdb_test: Connection, user_test: Connection) -> TestClient:
    app = create_api()
    # We use the lambda definitions because fixtures may not be called directly.
    app.dependency_overrides[expdb_connection] = lambda: expdb_test
    app.dependency_overrides[userdb_connection] = lambda: user_test
    return TestClient(app)


@pytest.fixture()
def dataset_130() -> Generator[dict[str, Any], None, None]:
    json_path = Path(__file__).parent / "resources" / "datasets" / "dataset_130.json"
    with json_path.open("r") as dataset_file:
        yield json.load(dataset_file)


@pytest.fixture()
def default_configuration_file() -> Path:
    return Path().parent.parent / "src" / "config.toml"
