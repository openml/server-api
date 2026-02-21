from collections.abc import Sequence
from typing import cast

from sqlalchemy import Connection, Row, text


def get_subflows(for_flow: int, expdb: Connection) -> Sequence[Row]:
    return cast(
        "Sequence[Row]",
        expdb.execute(
            text(
                """
            SELECT child as child_id, identifier
            FROM implementation_component
            WHERE parent = :flow_id
            """,
            ),
            parameters={"flow_id": for_flow},
        ),
    )


def get_tags(flow_id: int, expdb: Connection) -> list[str]:
    tag_rows = expdb.execute(
        text(
            """
            SELECT tag
            FROM implementation_tag
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": flow_id},
    )
    return [tag.tag for tag in tag_rows]


def get_parameters(flow_id: int, expdb: Connection) -> Sequence[Row]:
    return cast(
        "Sequence[Row]",
        expdb.execute(
            text(
                """
            SELECT *, defaultValue as default_value, dataType as data_type
            FROM input
            WHERE implementation_id = :flow_id
            """,
            ),
            parameters={"flow_id": flow_id},
        ),
    )


def tag(id_: int, tag_: str, *, user_id: int, connection: Connection) -> None:
    connection.execute(
        text(
            """
            INSERT INTO implementation_tag(`id`, `tag`, `uploader`)
            VALUES (:flow_id, :tag, :user_id)
            """,
        ),
        parameters={"flow_id": id_, "tag": tag_, "user_id": user_id},
    )


def get_tag(id_: int, tag_: str, connection: Connection) -> Row | None:
    return connection.execute(
        text(
            """
            SELECT `id`, `tag`, `uploader`
            FROM implementation_tag
            WHERE `id` = :flow_id AND `tag` = :tag
            """,
        ),
        parameters={"flow_id": id_, "tag": tag_},
    ).one_or_none()


def delete_tag(id_: int, tag_: str, connection: Connection) -> None:
    connection.execute(
        text(
            """
            DELETE FROM implementation_tag
            WHERE `id` = :flow_id AND `tag` = :tag
            """,
        ),
        parameters={"flow_id": id_, "tag": tag_},
    )


def get_by_name(name: str, external_version: str, expdb: Connection) -> Row | None:
    """Gets flow by name and external version."""
    return expdb.execute(
        text(
            """
            SELECT *, uploadDate as upload_date
            FROM implementation
            WHERE name = :name AND external_version = :external_version
            """,
        ),
        parameters={"name": name, "external_version": external_version},
    ).one_or_none()


def get(id_: int, expdb: Connection) -> Row | None:
    return expdb.execute(
        text(
            """
            SELECT *, uploadDate as upload_date
            FROM implementation
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": id_},
    ).one_or_none()
