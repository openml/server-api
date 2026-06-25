from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from sqlalchemy import Row, text

from routers.types import Identifier

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection


async def get(id_: Identifier, expdb: AsyncConnection) -> Row | None:
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


async def get_task_type(task_type_id: Identifier, expdb: AsyncConnection) -> Row | None:
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


async def get_task_type_name(task_id: int, expdb: AsyncConnection) -> str | None:
    """Fetch the human-readable task type name for the task associated with a run.

    Joins `task` and `task_type` on `ttid` to resolve the name
    (e.g. "Supervised Classification").
    """
    row = await expdb.execute(
        text(
            """
            SELECT `tt`.`name`
            FROM `task` `t`
            JOIN `task_type` `tt` ON `t`.`ttid` = `tt`.`ttid`
            WHERE `t`.`task_id` = :task_id
            """,
        ),
        parameters={"task_id": task_id},
    )
    result = row.one_or_none()
    return result.name if result else None


async def get_task_evaluation_measure(task_id: int, expdb: AsyncConnection) -> str | None:
    """Fetch the evaluation measure configured for a task, if any.

    Queries `task_inputs` for the row where `input = 'evaluation_measures'`.
    Returns None (not an empty string) when no such row exists, so callers
    can treat a falsy result uniformly.
    """
    row = await expdb.execute(
        text(
            """
            SELECT `value`
            FROM `task_inputs`
            WHERE `task_id` = :task_id
              AND `input` = 'evaluation_measures'
            """,
        ),
        parameters={"task_id": task_id},
    )
    result = row.one_or_none()
    return result.value if result else None


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


async def get_input_for_task(id_: Identifier, expdb: AsyncConnection) -> Sequence[Row]:
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
    task_type: Identifier,
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


async def get_tags(id_: Identifier, expdb: AsyncConnection) -> list[str]:
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
