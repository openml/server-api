from collections.abc import Sequence
from typing import cast

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncConnection

from database.tagging import insert_tag, remove_tag, select_tag, select_tags

_TABLE = "task_tag"
_ID_COLUMN = "id"


async def get(id_: int, expdb: AsyncConnection) -> Row | None:
    row = await expdb.execute(
        text(
            """
            SELECT *
            FROM task
            WHERE `task_id` = :task_id
            """,
        ),
        parameters={"task_id": id_},
    )
    return row.one_or_none()


async def get_task_types(expdb: AsyncConnection) -> Sequence[Row]:
    rows = await expdb.execute(
        text(
            """
       SELECT `ttid`, `name`, `description`, `creator`
       FROM task_type
       """,
        ),
    )
    return cast(
        "Sequence[Row]",
        rows.all(),
    )


async def get_task_type(task_type_id: int, expdb: AsyncConnection) -> Row | None:
    row = await expdb.execute(
        text(
            """
        SELECT *
        FROM task_type
        WHERE `ttid`=:ttid
        """,
        ),
        parameters={"ttid": task_type_id},
    )
    return row.one_or_none()


async def get_input_for_task_type(task_type_id: int, expdb: AsyncConnection) -> Sequence[Row]:
    rows = await expdb.execute(
        text(
            """
        SELECT *
        FROM task_type_inout
        WHERE `ttid`=:ttid AND `io`='input'
        """,
        ),
        parameters={"ttid": task_type_id},
    )
    return cast(
        "Sequence[Row]",
        rows.all(),
    )


async def get_input_for_task(id_: int, expdb: AsyncConnection) -> Sequence[Row]:
    rows = await expdb.execute(
        text(
            """
            SELECT `input`, `value`
            FROM task_inputs
            WHERE task_id = :task_id
            """,
        ),
        parameters={"task_id": id_},
    )
    return cast(
        "Sequence[Row]",
        rows.all(),
    )


async def get_task_type_inout_with_template(
    task_type: int,
    expdb: AsyncConnection,
) -> Sequence[Row]:
    rows = await expdb.execute(
        text(
            """
            SELECT *
            FROM task_type_inout
            WHERE `ttid`=:ttid AND `template_api` IS NOT NULL
            """,
        ),
        parameters={"ttid": task_type},
    )
    return cast(
        "Sequence[Row]",
        rows.all(),
    )


async def get_tags(id_: int, expdb: AsyncConnection) -> list[str]:
    return await select_tags(table=_TABLE, id_column=_ID_COLUMN, id_=id_, expdb=expdb)


async def tag(id_: int, tag_: str, *, user_id: int, expdb: AsyncConnection) -> None:
    await insert_tag(
        table=_TABLE,
        id_column=_ID_COLUMN,
        id_=id_,
        tag_=tag_,
        user_id=user_id,
        expdb=expdb,
    )


async def get_tag(id_: int, tag_: str, expdb: AsyncConnection) -> Row | None:
    return await select_tag(table=_TABLE, id_column=_ID_COLUMN, id_=id_, tag_=tag_, expdb=expdb)


async def delete_tag(id_: int, tag_: str, expdb: AsyncConnection) -> None:
    await remove_tag(table=_TABLE, id_column=_ID_COLUMN, id_=id_, tag_=tag_, expdb=expdb)
