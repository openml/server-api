import http.client
from typing import Annotated

from core.formatting import _str_to_bool
from database.studies import get_study_by_alias, get_study_by_id
from database.users import User, UserGroup
from fastapi import APIRouter, Depends, HTTPException
from schemas.core import Visibility
from schemas.study import Study, StudyType
from sqlalchemy import Connection, text

from routers.dependencies import expdb_connection, fetch_user

router = APIRouter(prefix="/studies", tags=["studies"])


@router.get("/{study_id}")
def get_study(
    study_id: int | str,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> Study:
    if isinstance(study_id, int) or study_id.isdigit():
        study = get_study_by_id(int(study_id), expdb)
    else:
        study = get_study_by_alias(study_id, expdb)
        study_id = study.id

    if study is None:
        raise HTTPException(status_code=http.client.NOT_FOUND, detail="Study not found.")
    if study.visibility == Visibility.PRIVATE:
        if user is None:
            raise HTTPException(status_code=http.client.UNAUTHORIZED, detail="Study is private.")
        if study.creator != user.user_id and UserGroup.ADMIN not in user.groups:
            raise HTTPException(status_code=http.client.FORBIDDEN, detail="Study is private.")
    if _str_to_bool(study.legacy):
        raise HTTPException(
            status_code=http.client.GONE,
            detail="Legacy studies are no longer supported",
        )

    if study.type_ == StudyType.TASK:
        study_data = expdb.execute(
            text(
                """
                SELECT ts.task_id as task_id, ti.value as data_id
                FROM task_study as ts LEFT JOIN task_inputs ti ON ts.task_id = ti.task_id
                WHERE ts.study_id = :study_id AND ti.input = 'source_data'
                """,
            ),
            parameters={"study_id": study_id},
        ).fetchall()
    else:
        study_data = expdb.execute(
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
            parameters={"study_id": study_id},
        ).fetchall()
    return Study(
        id_=study.id,
        name=study.name,
        alias=study.alias,
        main_entity_type=study.type_,
        description=study.description,
        visibility=study.visibility,
        status=study.status,
        creation_date=study.creation_date,
        creator=study.creator,
        data_ids=[row.data_id for row in study_data],
        task_ids=[row.task_id for row in study_data],
        run_ids=[row.run_id for row in study_data] if study.type_ == StudyType.RUN else [],
        flow_ids=[row.flow_id for row in study_data] if study.type_ == StudyType.RUN else [],
        setup_ids=[row.setup_id for row in study_data] if study.type_ == StudyType.RUN else [],
    )
