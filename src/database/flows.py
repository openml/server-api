from collections.abc import Sequence
from typing import cast

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncConnection

from database.tagging import insert_tag, remove_tag, select_tag, select_tags

_TABLE = "implementation_tag"
_ID_COLUMN = "id"


async def get_subflows(for_flow: int, expdb: AsyncConnection) -> Sequence[Row]:
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
    return cast(
        "Sequence[Row]",
        rows.all(),
    )


async def get_tags(flow_id: int, expdb: AsyncConnection) -> list[str]:
    return await select_tags(table=_TABLE, id_column=_ID_COLUMN, id_=flow_id, expdb=expdb)


async def get_parameters(flow_id: int, expdb: AsyncConnection) -> Sequence[Row]:
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
    return cast(
        "Sequence[Row]",
        rows.all(),
    )


async def tag(id_: int, tag_: str, *, user_id: int, expdb: AsyncConnection) -> None:
    await insert_tag(
        table=_TABLE, id_column=_ID_COLUMN, id_=id_, tag_=tag_, user_id=user_id, expdb=expdb,
    )


async def get_tag(id_: int, tag_: str, expdb: AsyncConnection) -> Row | None:
    return await select_tag(table=_TABLE, id_column=_ID_COLUMN, id_=id_, tag_=tag_, expdb=expdb)


async def delete_tag(id_: int, tag_: str, expdb: AsyncConnection) -> None:
    await remove_tag(table=_TABLE, id_column=_ID_COLUMN, id_=id_, tag_=tag_, expdb=expdb)


async def get_by_name(name: str, external_version: str, expdb: AsyncConnection) -> Row | None:
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


async def get(id_: int, expdb: AsyncConnection) -> Row | None:
    row = await expdb.execute(
        text(
            """
            SELECT *, uploadDate as upload_date
            FROM implementation
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": id_},
    )
    return row.one_or_none()
