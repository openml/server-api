from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncConnection

from database.tagging import insert_tag, remove_tag, select_tag, select_tags

_TABLE = "run_tag"
_ID_COLUMN = "id"


async def get(id_: int, expdb: AsyncConnection) -> Row | None:
    row = await expdb.execute(
        text(
            """
            SELECT *
            FROM run
            WHERE `id` = :run_id
            """,
        ),
        parameters={"run_id": id_},
    )
    return row.one_or_none()


async def get_tags(id_: int, expdb: AsyncConnection) -> list[str]:
    return await select_tags(table=_TABLE, id_column=_ID_COLUMN, id_=id_, expdb=expdb)


async def tag(id_: int, tag_: str, *, user_id: int, expdb: AsyncConnection) -> None:
    await insert_tag(
        table=_TABLE, id_column=_ID_COLUMN, id_=id_, tag_=tag_, user_id=user_id, expdb=expdb,
    )


async def get_tag(id_: int, tag_: str, expdb: AsyncConnection) -> Row | None:
    return await select_tag(table=_TABLE, id_column=_ID_COLUMN, id_=id_, tag_=tag_, expdb=expdb)


async def delete_tag(id_: int, tag_: str, expdb: AsyncConnection) -> None:
    await remove_tag(table=_TABLE, id_column=_ID_COLUMN, id_=id_, tag_=tag_, expdb=expdb)
