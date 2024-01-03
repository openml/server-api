from typing import Sequence, cast

from sqlalchemy import Connection, Row, text


def get_flow_subflows(flow_id: int, expdb: Connection) -> Sequence[Row]:
    return cast(
        Sequence[Row],
        expdb.execute(
            text(
                """
            SELECT child as child_id, identifier
            FROM implementation_component
            WHERE parent = :flow_id
            """,
            ),
            parameters={"flow_id": flow_id},
        ),
    )


def get_flow_tags(flow_id: int, expdb: Connection) -> list[str]:
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


def get_flow_parameters(flow_id: int, expdb: Connection) -> Sequence[Row]:
    return cast(
        Sequence[Row],
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


def get_flow(flow_id: int, expdb: Connection) -> Row | None:
    return expdb.execute(
        text(
            """
            SELECT *, uploadDate as upload_date
            FROM implementation
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": flow_id},
    ).one_or_none()
