from datetime import datetime
from typing import cast

from schemas.study import CreateStudy, StudyType
from sqlalchemy import Connection, Row, text

from database.users import User


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


def create_study(study: CreateStudy, user: User, expdb: Connection) -> int:
    expdb.execute(
        text(
            """
            INSERT INTO study (
                name, alias, benchmark_suite, main_entity_type, description,
                creator, legacy, creation_date
            )
            VALUES (
                :name, :alias, :benchmark_suite, :main_entity_type, :description,
                 :creator, 'n', :creation_date
            )
            """,
        ),
        parameters={
            "name": study.name,
            "alias": study.alias,
            "main_entity_type": study.main_entity_type,
            "description": study.description,
            "creator": user.user_id,
            "creation_date": datetime.now(),
            "benchmark_suite": study.benchmark_suite,
        },
    )
    (study_id,) = expdb.execute(text("""SELECT LAST_INSERT_ID();""")).fetchone()
    return cast(int, study_id)


def attach_task_to_study(task_id: int, study_id: int, user: User, expdb: Connection) -> None:
    expdb.execute(
        text(
            """
            INSERT INTO task_study (study_id, task_id, uploader)
            VALUES (:study_id, :task_id, :user_id)
            """,
        ),
        parameters={"study_id": study_id, "task_id": task_id, "user_id": user.user_id},
    )


def attach_run_to_study(run_id: int, study_id: int, user: User, expdb: Connection) -> None:
    expdb.execute(
        text(
            """
            INSERT INTO run_study (study_id, run_id, uploader)
            VALUES (:study_id, :run_id, :user_id)
            """,
        ),
        parameters={"study_id": study_id, "run_id": run_id, "user_id": user.user_id},
    )
