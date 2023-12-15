from sqlalchemy import Connection, Row, text


def get_study_by_id(study_id: int, connection: Connection) -> Row:
    return connection.execute(
        text(
            """
            SELECT *, main_entity_type as type_
            FROM study
            WHERE id = :study_id
            """,
        ),
        parameters={"study_id": study_id},
    ).fetchone()


def get_study_by_alias(alias: str, connection: Connection) -> Row:
    return connection.execute(
        text(
            """
            SELECT *, main_entity_type as type_
            FROM study
            WHERE alias = :study_id
            """,
        ),
        parameters={"study_id": alias},
    ).fetchone()
