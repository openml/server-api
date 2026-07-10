from typing import TYPE_CHECKING

import database.flows
from tests.conftest import Flow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_database_flow_exists(flow: Flow, expdb_session: AsyncSession) -> None:
    retrieved_flow = await database.flows.get_by_name(flow.name, flow.external_version, expdb_session)
    assert retrieved_flow is not None
    assert retrieved_flow.id == flow.id
    # when using actual ORM, can instead ensure _all_ fields match.


async def test_database_flow_exists_returns_none_if_no_match(expdb_session: AsyncSession) -> None:
    retrieved_flow = await database.flows.get_by_name(
        name="foo",
        external_version="bar",
        expdb=expdb_session,
    )
    assert retrieved_flow is None
