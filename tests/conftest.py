import contextlib
import datetime
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol

import _pytest.mark
import httpx
import pytest
from _pytest.config import Config  # noqa: TC002 used during collection by Pytest
from _pytest.nodes import Item
from sqlalchemy.orm import Session  # noqa: TC002 used during collection by Pytest
from asgi_lifespan import LifespanManager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    Configuration,
    DatabaseConfiguration,
    DevelopmentConfiguration,
    LoggingConfiguration,
    RoutingConfiguration,
)
from core.types import Identifier
from database.engine import expdb_database, user_database
from main import create_api
from routers.dependencies import (
    expdb_connection as expdb_connection_dep,
    userdb_connection as userdb_connection_dep,
    expdb_session as expdb_session_dep,
    userdb_session as userdb_session_dep,
)
from tests.users import OWNER_USER

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

PHP_API_URL = "http://php-api:80/api/v1/json"


@contextlib.asynccontextmanager
async def automatic_rollback(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as connection, connection.begin() as transaction:
        yield connection
        if transaction.is_active:
            await transaction.rollback()


@contextlib.asynccontextmanager
async def temporary_records(
    connection: AsyncConnection,
    insert_queries: Iterable[tuple[str, dict[str, Any] | None]],
    delete_queries: Iterable[tuple[str, dict[str, Any] | None]],
    *,
    persist: bool = False,
) -> AsyncIterator[None]:
    """Execute insert queries on enter and their corresponding delete queries on exit."""
    for query, parameters in insert_queries:
        await connection.execute(text(query), parameters=parameters)
    if persist:
        await connection.commit()

    try:
        yield
    finally:
        for query, parameters in delete_queries:
            await connection.execute(text(query), parameters=parameters)
        if persist:
            await connection.commit()


@pytest.fixture
async def expdb_connection() -> AsyncIterator[AsyncConnection]:
    async with automatic_rollback(expdb_database()) as connection:
        yield connection


@pytest.fixture
async def userdb_connection() -> AsyncIterator[AsyncConnection]:
    async with automatic_rollback(user_database()) as connection:
        yield connection


@pytest.fixture
async def expdb_session(expdb_connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(
        bind=expdb_connection, join_transaction_mode="create_savepoint"
    ) as session:
        yield session


@pytest.fixture
async def userdb_session(userdb_connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(
        bind=userdb_connection, join_transaction_mode="create_savepoint"
    ) as session:
        yield session


# The PHP API fixture can be session scoped since they do not need access to
# function-scoped database transactions.
@pytest.fixture(scope="session")
async def php_api() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(base_url=PHP_API_URL) as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
async def app() -> AsyncIterator[FastAPI]:
    config = Configuration(
        openml_database=DatabaseConfiguration(database="openml"),
        expdb_database=DatabaseConfiguration(database="openml_expdb"),
        development=DevelopmentConfiguration(allow_test_api_keys=True),
        routing=RoutingConfiguration(
            minio_url="http://minio:9000", server_url="http://php-api:80/"
        ),
        logging=[LoggingConfiguration(sink="sys.stderr", level="DEBUG")],
    )
    _app = create_api(config)
    async with LifespanManager(_app):
        yield _app


@pytest.fixture
async def py_api(
    expdb_connection: AsyncConnection,
    userdb_connection: AsyncConnection,
    expdb_session: AsyncSession,
    userdb_session: AsyncSession,
    app: FastAPI,
) -> AsyncIterator[httpx.AsyncClient]:
    """Create test client which automatically rolls back database updates on teardown."""
    # Using the function-scoped database fixtures automatically benefits the
    # automatic rollbacks, but also lets a test author write to a database
    # transaction that is shared with the app. That is, it enables:
    #
    # def my_test(expdb_session, py_api):
    #     expdb_session.execute(...)  # write some data  # noqa: ERA001
    #     py_api.get(...)  # read that data           # noqa: ERA001

    async def override_expdb_connection() -> AsyncIterator[AsyncConnection]:
        yield expdb_connection

    async def override_userdb_connection() -> AsyncIterator[AsyncConnection]:
        yield userdb_connection

    async def override_expdb_session() -> AsyncIterator[AsyncSession]:
        yield expdb_session

    async def override_userdb_session() -> AsyncIterator[AsyncSession]:
        yield userdb_session

    app.dependency_overrides[expdb_connection_dep] = override_expdb_connection
    app.dependency_overrides[userdb_connection_dep] = override_userdb_connection
    app.dependency_overrides[expdb_session_dep] = override_expdb_session
    app.dependency_overrides[userdb_session_dep] = override_userdb_session

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        yield client

    app.dependency_overrides[expdb_connection_dep] = expdb_connection_dep
    app.dependency_overrides[userdb_connection_dep] = userdb_connection_dep
    app.dependency_overrides[expdb_session_dep] = expdb_session_dep
    app.dependency_overrides[userdb_session_dep] = userdb_session_dep


@pytest.fixture
def dataset_130() -> Iterator[dict[str, Any]]:
    json_path = Path(__file__).parent / "resources" / "datasets" / "dataset_130.json"
    with json_path.open("r") as dataset_file:
        yield json.load(dataset_file)


class Task(NamedTuple):
    """To be replaced by an actual ORM class."""

    id: Identifier
    task_type: Identifier
    creator: Identifier


class TaskFactory(Protocol):
    def __call__(
        self,
        *,
        task_id: Identifier = 42_000,
        task_type: Identifier = 1,
        creator: Identifier = OWNER_USER.user_id,
    ) -> Awaitable[Task]: ...


def _create_identifier_factory() -> Callable[[], Identifier]:
    _identifier_counter: Identifier = 10_000_000

    def _get() -> Identifier:
        nonlocal _identifier_counter
        _identifier_counter += 1
        return _identifier_counter

    return _get


_identifier_factory = _create_identifier_factory()


@pytest.fixture
async def task_factory(
    expdb_session: AsyncSession,
) -> TaskFactory:
    async def create_task(
        *,
        task_id: Identifier | None = None,
        task_type: Identifier = 1,
        creator: Identifier = OWNER_USER.user_id,
    ) -> Task:
        task_id = task_id or _identifier_factory()

        await expdb_session.execute(
            text("""
                INSERT INTO task (task_id, ttid, creator) VALUES (:task_id, :ttid, :creator);
            """),
            params={"task_id": task_id, "ttid": task_type, "creator": creator},
        )
        return Task(task_id, task_type, creator)

    return create_task


class DatasetFactory(Protocol):
    def __call__(
        self, *, dataset_id: Identifier = 42_000, creator: Identifier = OWNER_USER.user_id
    ) -> Awaitable[Identifier]: ...


@pytest.fixture
async def dataset_factory(
    expdb_session: AsyncSession,
) -> DatasetFactory:
    async def create_dataset(
        *, dataset_id: Identifier | None = None, creator: Identifier = OWNER_USER.user_id
    ) -> Identifier:
        dataset_id = dataset_id or _identifier_factory()
        await expdb_session.execute(
            text("""
                INSERT INTO dataset
                (did, uploader, name, version, format, upload_date, licence, url, visibility)
                VALUES
                (:dataset_id, :creator, :name, 'dataset-version', 'dataset-format',
                :now, 'public', 'dataset-url', 'public');
            """),
            params={
                "dataset_id": dataset_id,
                "creator": creator,
                "now": datetime.datetime.now(tz=datetime.UTC),
                "name": f"dataset-name-{dataset_id}",
            },
        )
        return dataset_id

    return create_dataset


class Flow(NamedTuple):
    """To be replaced by an actual ORM class."""

    id: Identifier
    name: str
    external_version: str


@pytest.fixture
async def flow(expdb_session: AsyncSession) -> Flow:
    await expdb_session.execute(
        text(
            """
            INSERT INTO implementation(fullname,name,version,external_version,uploadDate)
            VALUES ('a','name',2,'external_version','2024-02-02 02:23:23');
            """,
        ),
    )
    result = await expdb_session.execute(text("""SELECT LAST_INSERT_ID();"""))
    (flow_id,) = result.one()
    return Flow(id=flow_id, name="name", external_version="external_version")


@pytest.fixture
async def persisted_flow(flow: Flow, expdb_session: AsyncSession) -> AsyncIterator[Flow]:
    await expdb_session.commit()
    yield flow
    # We want to ensure the commit below does not accidentally persist new
    # data to the database.
    await expdb_session.rollback()

    await expdb_session.execute(
        text(
            """
            DELETE FROM implementation
            WHERE id = :flow_id
            """,
        ),
        params={"flow_id": flow.id},
    )
    await expdb_session.commit()


@pytest.fixture
def temporary_tags(
    expdb_connection: AsyncConnection,
) -> Callable[..., contextlib.AbstractAsyncContextManager[None]]:
    @contextlib.asynccontextmanager
    async def _temporary_tags(
        table: str,
        tags: Iterable[str],
        identifier: Identifier,
        *,
        persist: bool = False,
    ) -> AsyncIterator[None]:
        insert_queries = [
            (
                f"INSERT INTO {table}(`id`,`tag`,`uploader`) VALUES (:identifier, :tag, :user_id);",  # noqa: S608  # No user provided values
                {
                    "identifier": identifier,
                    "tag": tag,
                    "user_id": OWNER_USER.user_id,
                },
            )
            for tag in tags
        ]
        delete_queries = [
            (
                f"DELETE FROM {table} WHERE `id`=:identifier AND `tag`=:tag",  # noqa: S608  # No user provided values
                {"identifier": identifier, "tag": tag},
            )
            for tag in tags
        ]
        async with temporary_records(
            connection=expdb_connection,
            insert_queries=insert_queries,
            delete_queries=delete_queries,
            persist=persist,
        ):
            yield

    return _temporary_tags


def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:  # noqa: ARG001
    for test_item in items:
        for fixture in test_item.fixturenames:  # type: ignore[attr-defined]
            test_item.own_markers.append(_pytest.mark.Mark(fixture, (), {}))
