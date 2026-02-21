from collections.abc import Sequence
from typing import cast

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncConnection


async def get_subflows(for_flow: int, expdb: AsyncConnection) -> Sequence[Row]:
    result = await expdb.execute(
        text(
            """
        SELECT child as child_id, identifier
        FROM implementation_component
        WHERE parent = :flow_id
        """,
        ),
        parameters={"flow_id": for_flow},
    )
    return cast("Sequence[Row]", result.all())


async def get_tags(flow_id: int, expdb: AsyncConnection) -> list[str]:
    tag_rows = await expdb.execute(
        text(
            """
            SELECT tag
            FROM implementation_tag
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": flow_id},
    )
    return [tag.tag for tag in tag_rows]


async def get_parameters(flow_id: int, expdb: AsyncConnection) -> Sequence[Row]:
    result = await expdb.execute(
        text(
            """
        SELECT *, defaultValue as default_value, dataType as data_type
        FROM input
        WHERE implementation_id = :flow_id
        """,
        ),
        parameters={"flow_id": flow_id},
    )
    return cast("Sequence[Row]", result.all())


async def get_by_name(name: str, external_version: str, expdb: AsyncConnection) -> Row | None:
    """Gets flow by name and external version."""
    result = await expdb.execute(
        text(
            """
            SELECT *, uploadDate as upload_date
            FROM implementation
            WHERE name = :name AND external_version = :external_version
            """,
        ),
        parameters={"name": name, "external_version": external_version},
    )
    return result.one_or_none()


async def get(id_: int, expdb: AsyncConnection) -> Row | None:
    result = await expdb.execute(
        text(
            """
            SELECT *, uploadDate as upload_date
            FROM implementation
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": id_},
    )
    return result.one_or_none()
