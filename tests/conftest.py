import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

import _pytest.mark
import httpx
import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item
from dotenv import load_dotenv
from sqlalchemy import Connection, text

load_dotenv()


PHP_API_URL = "http://openml-php-rest-api:80/api/v1/json"


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--use-testcontainer",  # CLI flag
        action="store_true",  # True if provided, False if omitted
        help="Use testcontainers for database tests",
    )


def pytest_configure(config: Config) -> None:
    use_test_container = config.getoption("--use-testcontainer")

    if use_test_container:
        config.pluginmanager.import_plugin("tests.fixtures_testcontainer")
    else:
        config.pluginmanager.import_plugin("tests.fixtures_local")


@pytest.fixture
def php_api() -> httpx.Client:
    with httpx.Client(base_url=PHP_API_URL) as client:
        yield client


@pytest.fixture
def dataset_130() -> Iterator[dict[str, Any]]:
    json_path = Path(__file__).parent / "resources" / "datasets" / "dataset_130.json"
    with json_path.open("r") as dataset_file:
        yield json.load(dataset_file)


@pytest.fixture
def default_configuration_file() -> Path:
    return Path().parent.parent / "src" / "config.toml"


class Flow(NamedTuple):
    """To be replaced by an actual ORM class."""

    id: int
    name: str
    external_version: str


@pytest.fixture
def flow(expdb_test: Connection) -> Flow:
    expdb_test.execute(
        text(
            """
            INSERT INTO implementation(fullname,name,version,external_version,uploadDate)
            VALUES ('a','name',2,'external_version','2024-02-02 02:23:23');
            """,
        ),
    )
    (flow_id,) = expdb_test.execute(text("""SELECT LAST_INSERT_ID();""")).one()
    return Flow(id=flow_id, name="name", external_version="external_version")


@pytest.fixture
def persisted_flow(flow: Flow, expdb_test: Connection) -> Iterator[Flow]:
    expdb_test.commit()
    yield flow
    # We want to ensure the commit below does not accidentally persist new
    # data to the database.
    expdb_test.rollback()

    expdb_test.execute(
        text(
            """
            DELETE FROM implementation
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": flow.id},
    )
    expdb_test.commit()


def pytest_collection_modifyitems(items: list[Item]) -> None:
    for test_item in items:
        for fixture in test_item.fixturenames:  # type: ignore[attr-defined]
            test_item.own_markers.append(_pytest.mark.Mark(fixture, (), {}))
