import re
from datetime import datetime
from typing import cast

from schemas.study import CreateStudy, StudyType
from sqlalchemy import Connection, Row, text

from database.users import User


def get_study_by_id(study_id: int, connection: Connection) -> Row | None:
    return connection.execute(
        text(
            """
            SELECT *, main_entity_type as type_
            FROM study
            WHERE id = :study_id
            """,
        ),
        parameters={"study_id": study_id},
    ).one_or_none()


def get_study_by_alias(alias: str, connection: Connection) -> Row | None:
    return connection.execute(
        text(
            """
            SELECT *, main_entity_type as type_
            FROM study
            WHERE alias = :study_id
            """,
        ),
        parameters={"study_id": alias},
    ).one_or_none()


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
            ).all(),
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
        ).all(),
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
    (study_id,) = expdb.execute(text("""SELECT LAST_INSERT_ID();""")).one()
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


def attach_tasks_to_study(
    study_id: int,
    task_ids: list[int],
    user: User,
    connection: Connection,
) -> None:
    to_link = [(study_id, task_id, user.user_id) for task_id in task_ids]
    try:
        connection.execute(
            text(
                """
                INSERT INTO task_study (study_id, task_id, uploader)
                VALUES (:study_id, :task_id, :user_id)
                """,
            ),
            parameters=[{"study_id": s, "task_id": t, "user_id": u} for s, t, u in to_link],
        )
    except Exception as e:
        (msg,) = e.args
        if match := re.search(r"Duplicate entry '(\d+)-(\d+)' for key 'task_study.PRIMARY'", msg):
            msg = f"Task {match.group(2)} is already attached to study {match.group(1)}."
        elif "a foreign key constraint fails" in msg:
            # The message and exception have no information about which task is invalid.
            msg = "One or more of the tasks do not exist."
        elif "Out of range value for column 'task_id'" in msg:
            msg = "One specified ids is not in the valid range of task ids."
        else:
            raise
        raise ValueError(msg) from e


def attach_runs_to_study(
    study_id: int,  # noqa: ARG001
    task_ids: list[int],  # noqa: ARG001
    user: User,  # noqa: ARG001
    connection: Connection,  # noqa: ARG001
) -> None:
    raise NotImplementedError
