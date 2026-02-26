from sqlalchemy import Connection, text
from sqlalchemy.engine import Row

def get(id_: int, connection: Connection) -> Row | None:
    """Get the setup by its ID."""
    row = connection.execute(
        text(
            """
            SELECT *
            FROM algorithm_setup
            WHERE sid = :setup_id
            """
        ),
        parameters={"setup_id": id_},
    )
    return row.one_or_none()

def get_tags_for(id_: int, connection: Connection) -> list[str]:
    """Get all tags for a specific setup."""
    rows = connection.execute(
        text(
            """
            SELECT tag
            FROM setup_tag
            WHERE id = :setup_id
            """
        ),
        parameters={"setup_id": id_},
    )
    return [row.tag for row in rows]

def tag(id_: int, tag_: str, *, user_id: int, connection: Connection) -> None:
    """Insert a new tag for the setup."""
    connection.execute(
        text(
            """
            INSERT INTO setup_tag(`id`, `tag`, `uploader`)
            VALUES (:setup_id, :tag, :user_id)
            """
        ),
        parameters={
            "setup_id": id_,
            "user_id": user_id,
            "tag": tag_,
        },
    )