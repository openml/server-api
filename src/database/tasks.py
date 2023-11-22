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
