from sqlalchemy import Connection

import database.flows
from tests.conftest import Flow


def test_database_flow_exists(flow: Flow, expdb_test: Connection) -> None:
    retrieved_flow = database.flows.get_by_name(flow.name, flow.external_version, expdb_test)
    assert retrieved_flow is not None
    assert retrieved_flow.id == flow.id


def test_database_flow_exists_returns_none_if_no_match(expdb_test: Connection) -> None:
    retrieved_flow = database.flows.get_by_name("foo", "bar", expdb_test)
    assert retrieved_flow is None
