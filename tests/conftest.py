import json
from enum import StrEnum
from pathlib import Path
from typing import Any, Generator

import pytest
from database.setup import expdb_database, user_database
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.dependencies import expdb_connection, userdb_connection
from sqlalchemy import Connection


class ApiKey(StrEnum):
    ADMIN: str = "AD000000000000000000000000000000"
    REGULAR_USER: str = "00000000000000000000000000000000"
    OWNER_USER: str = "DA1A0000000000000000000000000000"
    INVALID: str = "11111111111111111111111111111111"


@pytest.fixture()
def expdb_test() -> Connection:
    with expdb_database().connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture()
def user_test() -> Connection:
    with user_database().connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture()
def api_client(expdb_test: Connection, user_test: Connection) -> Generator[FastAPI, None, None]:
    # We want to avoid starting a test client app if tests don't need it.
    from main import app

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
