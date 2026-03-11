from sqlalchemy.ext.asyncio import AsyncConnection

import database.flows
from tests.conftest import Flow


async def test_database_flow_exists(flow: Flow, expdb_test: AsyncConnection) -> None:
    retrieved_flow = await database.flows.get_by_name(flow.name, flow.external_version, expdb_test)
    assert retrieved_flow is not None
    assert retrieved_flow.id == flow.id
    # when using actual ORM, can instead ensure _all_ fields match.


async def test_database_flow_exists_returns_none_if_no_match(expdb_test: AsyncConnection) -> None:
    retrieved_flow = await database.flows.get_by_name(
        name="foo",
        external_version="bar",
        expdb=expdb_test,
    )
    assert retrieved_flow is None
