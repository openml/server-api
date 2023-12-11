from typing import Any

from sqlalchemy import Connection, CursorResult, MappingResult, RowMapping, text


def get_task(task_id: int, expdb: Connection) -> RowMapping | None:
    task_row = expdb.execute(
        text(
            """
            SELECT *
            FROM task
            WHERE `task_id` = :task_id
            """,
        ),
        parameters={"task_id": task_id},
    )
    return next(task_row.mappings(), None)


def get_task_types(expdb: Connection) -> list[dict[str, str | int]]:
    rows = expdb.execute(
        text(
            """
       SELECT `ttid`, `name`, `description`, `creator`
       FROM task_type
       """,
        ),
    )
    return list(rows.mappings())


def get_task_type(task_type_id: int, expdb: Connection) -> RowMapping | None:
    row = expdb.execute(
        text(
            """
        SELECT *
        FROM task_type
        WHERE `ttid`=:ttid
        """,
        ),
        parameters={"ttid": task_type_id},
    )
    return next(row, None)


def get_input_for_task_type(task_type_id: int, expdb: Connection) -> CursorResult[Any]:
    return expdb.execute(
        text(
            """
        SELECT *
        FROM task_type_inout
        WHERE `ttid`=:ttid AND `io`='input'
        """,
        ),
        parameters={"ttid": task_type_id},
    )


def get_input_for_task(task_id: int, expdb: Connection) -> MappingResult:
    rows = expdb.execute(
        text(
            """
            SELECT `input`, `value`
            FROM task_inputs
            WHERE task_id = :task_id
            """,
        ),
        parameters={"task_id": task_id},
    )
    return rows.mappings()


def get_task_type_inout_with_template(task_type: int, expdb: Connection) -> CursorResult[Any]:
    return expdb.execute(
        text(
            """
            SELECT *
            FROM task_type_inout
            WHERE `ttid`=:ttid AND `template_api` IS NOT NULL
            """,
        ),
        parameters={"ttid": task_type},
    )


def get_tags_for_task(task_id: int, expdb: Connection) -> list[str]:
    tag_rows = expdb.execute(
        text(
            """
            SELECT `tag`
            FROM task_tag
            WHERE `id` = :task_id
            """,
        ),
        parameters={"task_id": task_id},
    )
    return [row.tag for row in tag_rows]
