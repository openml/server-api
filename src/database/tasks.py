from collections.abc import Sequence
from typing import cast

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncConnection


async def get(id_: int, expdb: AsyncConnection) -> Row | None:
    return (
        await expdb.execute(
            text(
                """
            SELECT *
            FROM task
            WHERE `task_id` = :task_id
            """,
            ),
            parameters={"task_id": id_},
        )
    ).one_or_none()


async def get_task_types(expdb: AsyncConnection) -> Sequence[Row]:
    return cast(
        "Sequence[Row]",
        (
            await expdb.execute(
                text(
                    """
       SELECT `ttid`, `name`, `description`, `creator`
       FROM task_type
       """,
                ),
            )
        ).all(),
    )


async def get_task_type(task_type_id: int, expdb: AsyncConnection) -> Row | None:
    return (
        await expdb.execute(
            text(
                """
        SELECT *
        FROM task_type
        WHERE `ttid`=:ttid
        """,
            ),
            parameters={"ttid": task_type_id},
        )
    ).one_or_none()


async def get_input_for_task_type(task_type_id: int, expdb: AsyncConnection) -> Sequence[Row]:
    return cast(
        "Sequence[Row]",
        (
            await expdb.execute(
                text(
                    """
        SELECT *
        FROM task_type_inout
        WHERE `ttid`=:ttid AND `io`='input'
        """,
                ),
                parameters={"ttid": task_type_id},
            )
        ).all(),
    )


async def get_input_for_task(id_: int, expdb: AsyncConnection) -> Sequence[Row]:
    return cast(
        "Sequence[Row]",
        (
            await expdb.execute(
                text(
                    """
            SELECT `input`, `value`
            FROM task_inputs
            WHERE task_id = :task_id
            """,
                ),
                parameters={"task_id": id_},
            )
        ).all(),
    )


async def get_task_type_inout_with_template(
    task_type: int, expdb: AsyncConnection
) -> Sequence[Row]:
    return cast(
        "Sequence[Row]",
        (
            await expdb.execute(
                text(
                    """
            SELECT *
            FROM task_type_inout
            WHERE `ttid`=:ttid AND `template_api` IS NOT NULL
            """,
                ),
                parameters={"ttid": task_type},
            )
        ).all(),
    )


async def get_tags(id_: int, expdb: AsyncConnection) -> list[str]:
    tag_rows = await expdb.execute(
        text(
            """
            SELECT `tag`
            FROM task_tag
            WHERE `id` = :task_id
            """,
        ),
        parameters={"task_id": id_},
    )
    return [row.tag for row in tag_rows]
