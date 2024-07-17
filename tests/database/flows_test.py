from typing import NamedTuple

import database.flows
import pytest
from sqlalchemy import Connection, text


class Flow(NamedTuple):
    """To be replaced by an actual ORM class."""

    id: int
    name: str
    external_version: str


@pytest.fixture()
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


def test_database_flow_exists(flow: Flow, expdb_test: Connection) -> None:
    retrieved_flow = database.flows.get_by_name(flow.name, flow.external_version, expdb_test)
    assert retrieved_flow.id == flow.id
    # when using actual ORM, can instead ensure _all_ fields match.


def test_database_flow_exists_returns_none_if_no_match(expdb_test: Connection) -> None:
    retrieved_flow = database.flows.get_by_name(
        name="foo",
        external_version="bar",
        expdb=expdb_test,
    )
    assert retrieved_flow is None
