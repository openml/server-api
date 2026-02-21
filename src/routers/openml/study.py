from http import HTTPStatus
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncConnection

import database.studies
from core.formatting import _str_to_bool
from database.users import User, UserGroup
from routers.dependencies import expdb_connection, fetch_user
from schemas.core import Visibility
from schemas.study import CreateStudy, Study, StudyStatus, StudyType

router = APIRouter(prefix="/studies", tags=["studies"])


async def _get_study_raise_otherwise(
    id_or_alias: int | str,
    user: User | None,
    expdb: AsyncConnection,
) -> Row:
    if isinstance(id_or_alias, int) or id_or_alias.isdigit():
        study = await database.studies.get_by_id(int(id_or_alias), expdb)
    else:
        study = await database.studies.get_by_alias(id_or_alias, expdb)

    if study is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Study not found.")
    if study.visibility == Visibility.PRIVATE:
        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Must authenticate for private study.",
            )
        user_groups = await user.get_groups()
        if study.creator != user.user_id and UserGroup.ADMIN not in user_groups:
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Study is private.")
    if _str_to_bool(study.legacy):
        raise HTTPException(
            status_code=HTTPStatus.GONE,
            detail="Legacy studies are no longer supported",
        )
    return study


class AttachDetachResponse(BaseModel):
    study_id: int
    main_entity_type: StudyType


@router.post("/attach")
async def attach_to_study(
    study_id: Annotated[int, Body()],
    entity_ids: Annotated[list[int], Body()],
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)] = None,
) -> AttachDetachResponse:
    if user is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="User not found.")
    study = await _get_study_raise_otherwise(study_id, user, expdb)
    # PHP lets *anyone* edit *any* study. We're not going to do that.
    user_groups = await user.get_groups()
    if study.creator != user.user_id and UserGroup.ADMIN not in user_groups:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Study can only be edited by its creator.",
        )
    if study.status != StudyStatus.IN_PREPARATION:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Study can only be edited while in preparation.",
        )

    # We let the database handle the constraints on whether
    # the entity is already attached or if it even exists.
    attach_kwargs = {
        "study_id": study_id,
        "user": user,
        "connection": expdb,
    }
    try:
        if study.type_ == StudyType.TASK:
            await database.studies.attach_tasks(task_ids=entity_ids, **attach_kwargs)
        else:
            await database.studies.attach_runs(run_ids=entity_ids, **attach_kwargs)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=str(e),
        ) from None
    return AttachDetachResponse(study_id=study_id, main_entity_type=study.type_)


@router.post("/")
async def create_study(
    study: CreateStudy,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)] = None,
) -> dict[Literal["study_id"], int]:
    if user is None:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Creating a study requires authentication.",
        )
    if study.main_entity_type == StudyType.RUN and study.tasks:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Cannot create a run study with tasks.",
        )
    if study.main_entity_type == StudyType.TASK and study.runs:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Cannot create a task study with runs.",
        )
    if study.alias and await database.studies.get_by_alias(study.alias, expdb):
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Study alias already exists.",
        )
    study_id = await database.studies.create(study, user, expdb)
    if study.main_entity_type == StudyType.TASK:
        for task_id in study.tasks:
            await database.studies.attach_task(task_id, study_id, user, expdb)
    if study.main_entity_type == StudyType.RUN:
        for run_id in study.runs:
            await database.studies.attach_run(
                run_id=run_id,
                study_id=study_id,
                user=user,
                expdb=expdb,
            )
    # Make sure that invalid fields raise an error (e.g., "task_ids")
    return {"study_id": study_id}


@router.get("/{alias_or_id}")
async def get_study(
    alias_or_id: int | str,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)] = None,
) -> Study:
    study = await _get_study_raise_otherwise(alias_or_id, user, expdb)
    study_data = await database.studies.get_study_data(study, expdb)
    return Study(
        _legacy=_str_to_bool(study.legacy),
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
