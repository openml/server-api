import database.flows
from sqlalchemy import Connection

from tests.conftest import Flow


def test_database_flow_exists(flow: Flow, expdb_test: Connection) -> None:
    retrieved_flow = database.flows.get_by_name(flow.name, flow.external_version, expdb_test)
    assert retrieved_flow is not None
    assert retrieved_flow.id == flow.id
    # when using actual ORM, can instead ensure _all_ fields match.


def test_database_flow_exists_returns_none_if_no_match(expdb_test: Connection) -> None:
    retrieved_flow = database.flows.get_by_name(
        name="foo",
        external_version="bar",
        expdb=expdb_test,
    )
    assert retrieved_flow is None
