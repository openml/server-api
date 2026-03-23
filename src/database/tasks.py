from collections.abc import Sequence
from typing import cast

from sqlalchemy import Row, RowMapping, text
from sqlalchemy.ext.asyncio import AsyncConnection


ALLOWED_LOOKUP_TABLES = ["estimation_procedure", "evaluation_measure", "task_type", "dataset"]
PK_MAPPING = {
    "task_type": "ttid",
    "dataset": "did",
}


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
    rows = await expdb.execute(
        text(
            """
            SELECT `tag`
            FROM task_tag
            WHERE `id` = :task_id
            """,
        ),
        parameters={"task_id": id_},
    )
    tag_rows = rows.all()
    return [row.tag for row in tag_rows]


async def get_lookup_data(table: str, id_: int, expdb: AsyncConnection) -> RowMapping | None:
    if table not in ALLOWED_LOOKUP_TABLES:
        msg = f"Table {table} is not allowed for lookup."
        raise ValueError(msg)

    pk = PK_MAPPING.get(table, "id")
    result = await expdb.execute(
        text(
            f"""
            SELECT *
            FROM {table}
            WHERE `{pk}` = :id_
            """,  # noqa: S608
        ),
        parameters={"id_": id_},
    )
    return result.mappings().one_or_none()
