from typing import cast

from schemas.study import StudyType
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


def get_study_data(study: Row, expdb: Connection) -> list[Row]:
    if study.type_ == StudyType.TASK:
        return cast(
            list[Row],
            expdb.execute(
                text(
                    """
                SELECT ts.task_id as task_id, ti.value as data_id
                FROM task_study as ts LEFT JOIN task_inputs ti ON ts.task_id = ti.task_id
                WHERE ts.study_id = :study_id AND ti.input = 'source_data'
                """,
                ),
                parameters={"study_id": study.id},
            ).fetchall(),
        )
    return cast(
        list[Row],
        expdb.execute(
            text(
                """
            SELECT
                rs.run_id as run_id,
                run.task_id as task_id,
                run.setup as setup_id,
                ti.value as data_id,
                setup.implementation_id as flow_id
            FROM run_study as rs
            JOIN run ON run.rid = rs.run_id
            JOIN algorithm_setup as setup ON setup.sid = run.setup
            JOIN task_inputs as ti ON ti.task_id = run.task_id
            WHERE rs.study_id = :study_id AND ti.input = 'source_data'
            """,
            ),
            parameters={"study_id": study.id},
        ).fetchall(),
    )
