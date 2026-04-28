"""Database queries for run-related data."""

from collections.abc import Sequence
from typing import cast

from sqlalchemy import Row, bindparam, text
from sqlalchemy.ext.asyncio import AsyncConnection


async def exist(id_: int, expdb: AsyncConnection) -> bool:
    """Check if a run exists by ID."""
    row = await expdb.execute(
        text(
            """
            SELECT 1
            FROM `run`
            WHERE `rid` = :run_id
            """,
        ),
        parameters={"run_id": id_},
    )
    return bool(row.one_or_none())


async def get(run_id: int, expdb: AsyncConnection) -> Row | None:
    """Fetch the core run row from the `run` table.

    Returns the row if found, or None if no run with `run_id` exists.
    The `error_message` column is NULL when the run completed without errors.
    """
    row = await expdb.execute(
        text(
            """
            SELECT `rid`, `uploader`, `setup`, `task_id`, `error_message`
            FROM `run`
            WHERE `rid` = :run_id
            """,
        ),
        parameters={"run_id": run_id},
    )
    return row.one_or_none()


async def get_uploader_name(uploader_id: int, userdb: AsyncConnection) -> str | None:
    """Fetch the display name of a user from the openml database.

    Queries the `users` table in the separate openml DB and concatenates
    first_name + ' ' + last_name. Returns None if the user does not exist.
    """
    row = await userdb.execute(
        text(
            """
            SELECT CONCAT_WS(' ', `first_name`, `last_name`) AS `name`
            FROM `users`
            WHERE `id` = :uploader_id
            """,
        ),
        parameters={"uploader_id": uploader_id},
    )
    result = row.one_or_none()
    return result.name if result else None


async def get_tags(run_id: int, expdb: AsyncConnection) -> list[str]:
    """Fetch all tags associated with a run from the `run_tag` table.

    The `id` column in `run_tag` refers to the run ID
    """
    rows = await expdb.execute(
        text(
            """
            SELECT `tag`
            FROM `run_tag`
            WHERE `id` = :run_id
            """,
        ),
        parameters={"run_id": run_id},
    )
    return [row.tag for row in rows.all()]


async def get_input_data(run_id: int, expdb: AsyncConnection) -> list[Row]:
    """Fetch the dataset(s) used as input for a run, with name and url.

    Joins `input_data` with `dataset` to include the dataset name and ARFF URL.
    """
    rows = await expdb.execute(
        text(
            """
            SELECT `id`.`data` AS `did`, `d`.`name`, `d`.`url`
            FROM `input_data` `id`
            JOIN `dataset` `d` ON `id`.`data` = `d`.`did`
            WHERE `id`.`run` = :run_id
            """,
        ),
        parameters={"run_id": run_id},
    )
    return cast("list[Row]", rows.all())


async def get_output_files(run_id: int, expdb: AsyncConnection) -> list[Row]:
    """Fetch output files attached to a run from the `runfile` table.

    Typical entries include the description XML and predictions ARFF.
    The `field` column holds the file label (e.g. "description", "predictions").

    Note: the PHP response includes a deprecated `did` field hardcoded to "-1"
    for each file. This implementation omits it entirely.
    """
    rows = await expdb.execute(
        text(
            """
            SELECT `file_id`, `field`
            FROM `runfile`
            WHERE `source` = :run_id
            """,
        ),
        parameters={"run_id": run_id},
    )
    return cast("list[Row]", rows.all())


async def get_evaluations(
    run_id: int,
    expdb: AsyncConnection,
    *,
    evaluation_engine_ids: list[int],
) -> list[Row]:
    """Fetch evaluation metric results for a run.

    Joins `evaluation` with `math_function` to resolve the metric name
    (the `evaluation` table stores only a `function_id`, not the name directly).

    Filters by `evaluation_engine_id IN (...)`. The list is configurable
    via `config.toml [run] evaluation_engine_ids`.
    Dynamic named parameters are used for aiomysql compatibility.
    """
    if not evaluation_engine_ids:
        return []

    query = text(
        """
        SELECT `m`.`name`, `e`.`value`, `e`.`array_data`
        FROM `evaluation` `e`
        JOIN `math_function` `m` ON `e`.`function_id` = `m`.`id`
        WHERE `e`.`source` = :run_id
          AND `e`.`evaluation_engine_id` IN :engine_ids
        """,
    ).bindparams(bindparam("engine_ids", expanding=True))
    rows = await expdb.execute(
        query,
        parameters={"run_id": run_id, "engine_ids": evaluation_engine_ids},
    )
    return cast("list[Row]", rows.all())


async def get_task_type(task_id: int, expdb: AsyncConnection) -> str | None:
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


async def get_trace(run_id: int, expdb: AsyncConnection) -> Sequence[Row]:
    """Get trace rows for a run from the trace table."""
    rows = await expdb.execute(
        text(
            """
            SELECT `repeat`, `fold`, `iteration`, `setup_string`, `evaluation`, `selected`
            FROM `trace`
            WHERE `run_id` = :run_id
            """,
        ),
        parameters={"run_id": run_id},
    )
    return cast(
        "Sequence[Row]",
        rows.all(),
    )
