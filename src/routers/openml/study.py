import http.client
from typing import Annotated

from core.formatting import _str_to_bool
from database.users import User, UserGroup
from fastapi import APIRouter, Depends, HTTPException
from schemas.core import Visibility
from schemas.study import Study, StudyType
from sqlalchemy import Connection, text

from routers.dependencies import expdb_connection, fetch_user

router = APIRouter(prefix="/studies", tags=["studies"])


@router.get("/{study_id}")
def get_study(
    study_id: int,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> Study:
    # study_id may also be an alias instead

    study = expdb.execute(
        text(
            """
            SELECT *
            FROM study
            WHERE id = :study_id
            """,
        ),
        parameters={"study_id": study_id},
    ).fetchone()
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

    if study.main_entity_type == StudyType.TASK:
        tasks = expdb.execute(
            text(
                """
                SELECT ts.task_id as task_id, ti.value as data_id
                FROM task_study as ts LEFT JOIN task_inputs ti ON ts.task_id = ti.task_id
                WHERE ts.study_id = :study_id AND ti.input = 'source_data'
                """,
            ),
            parameters={"study_id": study_id},
        ).fetchall()
        task_ids = [task.task_id for task in tasks]
        data_ids = [task.data_id for task in tasks]
    else:
        msg = "Only task studies are supported."
        raise NotImplementedError(msg)
    run_ids: list[int] = []
    return Study(
        id_=study.id,
        name=study.name,
        alias=study.alias,
        main_entity_type=study.main_entity_type,
        description=study.description,
        visibility=study.visibility,
        status=study.status,
        creation_date=study.creation_date,
        creator=study.creator,
        task_ids=task_ids,
        run_ids=run_ids,
        data_ids=data_ids,
        # flow_ids=study.flow_ids,
        # setup_ids=study.setup_ids,
    )
