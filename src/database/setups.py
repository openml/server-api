from sqlalchemy import Connection, text
from sqlalchemy.engine import Row


def get(setup_id: int, connection: Connection) -> Row | None:
    row = connection.execute(
        text(
            """
            SELECT *
            FROM algorithm_setup
            WHERE sid = :setup_id
            """,
        ),
        parameters={"setup_id": setup_id},
    )
    return row.first()


def get_tags(setup_id: int, connection: Connection) -> list[Row]:
    rows = connection.execute(
        text(
            """
            SELECT *
            FROM setup_tag
            WHERE id = :setup_id
            """,
        ),
        parameters={"setup_id": setup_id},
    )
    return list(rows.all())


def untag(setup_id: int, tag: str, connection: Connection) -> None:
    connection.execute(
        text(
            """
            DELETE FROM setup_tag
            WHERE id = :setup_id AND tag = :tag
            """,
        ),
        parameters={"setup_id": setup_id, "tag": tag},
    )
