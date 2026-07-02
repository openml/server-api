from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import text

from database.schema.base import UntypedRow
from routers.types import Identifier

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection


async def get_subflows(for_flow: Identifier, expdb: AsyncConnection) -> Sequence[UntypedRow]:
    rows = await expdb.execute(
        text(
            """
            SELECT child as child_id, identifier
            FROM implementation_component
            WHERE parent = :flow_id
            """,
        ),
        parameters={"flow_id": for_flow},
    )
    return rows.all()


async def get_tags(flow_id: Identifier, expdb: AsyncConnection) -> list[str]:
    rows = await expdb.execute(
        text(
            """
            SELECT tag
            FROM implementation_tag
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": flow_id},
    )
    tag_rows = rows.all()
    return [tag.tag for tag in tag_rows]


async def get_parameters(flow_id: Identifier, expdb: AsyncConnection) -> Sequence[UntypedRow]:
    rows = await expdb.execute(
        text(
            """
            SELECT *, defaultValue as default_value, dataType as data_type
            FROM input
            WHERE implementation_id = :flow_id
            """,
        ),
        parameters={"flow_id": flow_id},
    )
    return rows.all()


async def get_by_name(
    name: str,
    external_version: str,
    expdb: AsyncConnection,
) -> UntypedRow | None:
    """Get flow by name and external version."""
    row = await expdb.execute(
        text(
            """
            SELECT *, uploadDate as upload_date
            FROM implementation
            WHERE name = :name AND external_version = :external_version
            """,
        ),
        parameters={"name": name, "external_version": external_version},
    )
    return row.one_or_none()


async def get(id_: Identifier, expdb: AsyncConnection) -> UntypedRow | None:
    row = await expdb.execute(
        text(
            """
            SELECT *, uploadDate as upload_date, fullName AS full_name
            FROM implementation
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": id_},
    )
    return row.one_or_none()
