from sqlalchemy import Connection, text


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


def get_task_type(task_type_id: int, expdb: Connection) -> dict[str, str | int] | None:
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
    task_type = dict(next(row.mappings(), {}))
    return task_type or None


def get_input_for_task_type(task_type_id: int, expdb: Connection) -> list[dict[str, str | int]]:
    rows = expdb.execute(
        text(
            """
        SELECT *
        FROM task_type_inout
        WHERE `ttid`=:ttid AND `io`='input'
        """,
        ),
        parameters={"ttid": task_type_id},
    )
    return [dict(row) for row in rows.mappings()]
