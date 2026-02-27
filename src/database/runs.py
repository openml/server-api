from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import cast

from sqlalchemy import Connection, Row, text


def get(run_id: int, expdb: Connection) -> Row | None:
    """Fetch a single run row by its primary key."""
    return expdb.execute(
        text(
            """
            SELECT `rid`, `task_id`, `implementation_id` AS `flow_id`,
                   `uploader`, `upload_time`, `setup_string`
            FROM run
            WHERE `rid` = :run_id
            """,
        ),
        parameters={"run_id": run_id},
    ).one_or_none()


def create(
    *,
    task_id: int,
    flow_id: int,
    uploader_id: int,
    setup_string: str | None,
    expdb: Connection,
) -> int:
    """Insert a new run row and return the generated run_id."""
    expdb.execute(
        text(
            """
            INSERT INTO run(
                `task_id`, `implementation_id`, `uploader`,
                `upload_time`, `setup_string`
            )
            VALUES (:task_id, :flow_id, :uploader_id, :upload_time, :setup_string)
            """,
        ),
        parameters={
            "task_id": task_id,
            "flow_id": flow_id,
            "uploader_id": uploader_id,
            "upload_time": datetime.datetime.now(),
            "setup_string": setup_string,
        },
    )
    row = expdb.execute(text("SELECT LAST_INSERT_ID()")).one()
    return int(row[0])


def get_tags(run_id: int, expdb: Connection) -> list[str]:
    """Return all tags for a given run."""
    rows = expdb.execute(
        text(
            """
            SELECT `tag`
            FROM run_tag
            WHERE `id` = :run_id
            """,
        ),
        parameters={"run_id": run_id},
    )
    return [row.tag for row in rows]


def get_evaluations(run_id: int, expdb: Connection) -> Sequence[Row]:
    """Return all evaluation measure rows for a given run."""
    return cast(
        "Sequence[Row]",
        expdb.execute(
            text(
                """
                SELECT `function`, `value`, `array_data`
                FROM run_measure
                WHERE `run_id` = :run_id
                """,
            ),
            parameters={"run_id": run_id},
        ).all(),
    )


def store_evaluation(
    *,
    run_id: int,
    function: str,
    value: float | None,
    array_data: str | None = None,
    expdb: Connection,
) -> None:
    """Insert or update a single evaluation measure for a run."""
    expdb.execute(
        text(
            """
            INSERT INTO run_measure(`run_id`, `function`, `value`, `array_data`)
            VALUES (:run_id, :function, :value, :array_data)
            ON DUPLICATE KEY UPDATE `value` = :value, `array_data` = :array_data
            """,
        ),
        parameters={
            "run_id": run_id,
            "function": function,
            "value": value,
            "array_data": array_data,
        },
    )


def delete(run_id: int, expdb: Connection) -> None:
    """Delete a run row by primary key (used for rollback on enqueue failure)."""
    expdb.execute(
        text("DELETE FROM run WHERE `rid` = :run_id"),
        parameters={"run_id": run_id},
    )
