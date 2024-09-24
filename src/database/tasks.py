from collections.abc import Sequence
from typing import cast

from sqlalchemy import Connection, Row, text


def get(id_: int, expdb: Connection) -> Row | None:
    return expdb.execute(
        text(
            """
            SELECT *
            FROM task
            WHERE `task_id` = :task_id
            """,
        ),
        parameters={"task_id": id_},
    ).one_or_none()


def get_task_types(expdb: Connection) -> Sequence[Row]:
    return cast(
        Sequence[Row],
        expdb.execute(
            text(
                """
       SELECT `ttid`, `name`, `description`, `creator`
       FROM task_type
       """,
            ),
        ).all(),
    )


def get_task_type(task_type_id: int, expdb: Connection) -> Row | None:
    return expdb.execute(
        text(
            """
        SELECT *
        FROM task_type
        WHERE `ttid`=:ttid
        """,
        ),
        parameters={"ttid": task_type_id},
    ).one_or_none()


def get_input_for_task_type(task_type_id: int, expdb: Connection) -> Sequence[Row]:
    return cast(
        Sequence[Row],
        expdb.execute(
            text(
                """
        SELECT *
        FROM task_type_inout
        WHERE `ttid`=:ttid AND `io`='input'
        """,
            ),
            parameters={"ttid": task_type_id},
        ).all(),
    )


def get_input_for_task(id_: int, expdb: Connection) -> Sequence[Row]:
    return cast(
        Sequence[Row],
        expdb.execute(
            text(
                """
            SELECT `input`, `value`
            FROM task_inputs
            WHERE task_id = :task_id
            """,
            ),
            parameters={"task_id": id_},
        ).all(),
    )


def get_task_type_inout_with_template(task_type: int, expdb: Connection) -> Sequence[Row]:
    return cast(
        Sequence[Row],
        expdb.execute(
            text(
                """
            SELECT *
            FROM task_type_inout
            WHERE `ttid`=:ttid AND `template_api` IS NOT NULL
            """,
            ),
            parameters={"ttid": task_type},
        ).all(),
    )


def get_tags(id_: int, expdb: Connection) -> list[str]:
    tag_rows = expdb.execute(
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
