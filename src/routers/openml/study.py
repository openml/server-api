from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy import Connection, Row
from sqlalchemy.exc import IntegrityError

import database.studies
from core.errors import (
    AuthenticationRequiredError,
    StudyAliasExistsError,
    StudyConflictError,
    StudyInvalidTypeError,
    StudyLegacyError,
    StudyNotEditableError,
    StudyNotFoundError,
    StudyPrivateError,
)
from core.formatting import _str_to_bool
from database.users import User, UserGroup
from routers.dependencies import expdb_connection, fetch_user
from schemas.core import Visibility
from schemas.study import CreateStudy, Study, StudyStatus, StudyType

router = APIRouter(prefix="/studies", tags=["studies"])


def _get_study_raise_otherwise(id_or_alias: int | str, user: User | None, expdb: Connection) -> Row:
    if isinstance(id_or_alias, int) or id_or_alias.isdigit():
        study = database.studies.get_by_id(int(id_or_alias), expdb)
    else:
        study = database.studies.get_by_alias(id_or_alias, expdb)

    if study is None:
        msg = "Study not found."
        raise StudyNotFoundError(msg)
    if study.visibility == Visibility.PRIVATE:
        if user is None:
            msg = "Must authenticate for private study."
            raise AuthenticationRequiredError(msg)
        if study.creator != user.user_id and UserGroup.ADMIN not in user.groups:
            msg = "Study is private."
            raise StudyPrivateError(msg)
    if _str_to_bool(study.legacy):
        msg = "Legacy studies are no longer supported."
        raise StudyLegacyError(msg)
    return study


class AttachDetachResponse(BaseModel):
    study_id: int
    main_entity_type: StudyType


@router.post("/attach")
def attach_to_study(
    study_id: Annotated[int, Body()],
    entity_ids: Annotated[list[int], Body()],
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> AttachDetachResponse:
    if user is None:
        msg = "Authentication required."
        raise AuthenticationRequiredError(msg)
    study = _get_study_raise_otherwise(study_id, user, expdb)
    # PHP lets *anyone* edit *any* study. We're not going to do that.
    if study.creator != user.user_id and UserGroup.ADMIN not in user.groups:
        msg = "Study can only be edited by its creator."
        raise StudyNotEditableError(msg)
    if study.status != StudyStatus.IN_PREPARATION:
        msg = "Study can only be edited while in preparation."
        raise StudyNotEditableError(msg)

    # We let the database handle the constraints on whether
    # the entity is already attached or if it even exists.
    attach_kwargs = {
        "study_id": study_id,
        "user": user,
        "connection": expdb,
    }
    try:
        if study.type_ == StudyType.TASK:
            database.studies.attach_tasks(task_ids=entity_ids, **attach_kwargs)
        else:
            database.studies.attach_runs(run_ids=entity_ids, **attach_kwargs)
    except ValueError as e:
        msg = str(e)
        raise StudyConflictError(msg) from e
    return AttachDetachResponse(study_id=study_id, main_entity_type=study.type_)


@router.post("/")
def create_study(
    study: CreateStudy,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[Literal["study_id"], int]:
    if user is None:
        msg = "Creating a study requires authentication."
        raise AuthenticationRequiredError(msg)
    if study.main_entity_type == StudyType.RUN and study.tasks:
        msg = "Cannot create a run study with tasks."
        raise StudyInvalidTypeError(msg)
    if study.main_entity_type == StudyType.TASK and study.runs:
        msg = "Cannot create a task study with runs."
        raise StudyInvalidTypeError(msg)
    if study.alias and database.studies.get_by_alias(study.alias, expdb):
        msg = "Study alias already exists."
        raise StudyAliasExistsError(msg)
    
    try:
        study_id = database.studies.create(study, user, expdb)
    except IntegrityError:
        # Race condition: another request created a study with this alias
        # between our check and insert
        msg = "Study alias already exists."
        raise StudyAliasExistsError(msg) from None
    
    if study.main_entity_type == StudyType.TASK:
        for task_id in study.tasks:
            database.studies.attach_task(task_id, study_id, user, expdb)
    if study.main_entity_type == StudyType.RUN:
        for run_id in study.runs:
            database.studies.attach_run(run_id=run_id, study_id=study_id, user=user, expdb=expdb)
    # Make sure that invalid fields raise an error (e.g., "task_ids")
    return {"study_id": study_id}


@router.get("/{alias_or_id}")
def get_study(
    alias_or_id: int | str,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> Study:
    study = _get_study_raise_otherwise(alias_or_id, user, expdb)
    study_data = database.studies.get_study_data(study, expdb)
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
