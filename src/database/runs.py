from sqlalchemy import Connection, Row, text


def get_tags(id_: int, expdb: Connection) -> list[str]:
    tag_rows = expdb.execute(
        text(
            """
            SELECT `tag`
            FROM run_tag
            WHERE `id` = :run_id
            """,
        ),
        parameters={"run_id": id_},
    )
    return [row.tag for row in tag_rows]


def tag(id_: int, tag_: str, *, user_id: int, connection: Connection) -> None:
    connection.execute(
        text(
            """
            INSERT INTO run_tag(`id`, `tag`, `uploader`)
            VALUES (:run_id, :tag, :user_id)
            """,
        ),
        parameters={"run_id": id_, "tag": tag_, "user_id": user_id},
    )


def get_tag(id_: int, tag_: str, connection: Connection) -> Row | None:
    return connection.execute(
        text(
            """
            SELECT `id`, `tag`, `uploader`
            FROM run_tag
            WHERE `id` = :run_id AND `tag` = :tag
            """,
        ),
        parameters={"run_id": id_, "tag": tag_},
    ).one_or_none()


def delete_tag(id_: int, tag_: str, connection: Connection) -> None:
    connection.execute(
        text(
            """
            DELETE FROM run_tag
            WHERE `id` = :run_id AND `tag` = :tag
            """,
        ),
        parameters={"run_id": id_, "tag": tag_},
    )
