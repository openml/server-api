import http.client
from typing import Annotated

from core.formatting import _str_to_bool
from database.studies import get_study_by_alias, get_study_by_id, get_study_data
from database.users import User, UserGroup
from fastapi import APIRouter, Depends, HTTPException
from schemas.core import Visibility
from schemas.study import Study, StudyType
from sqlalchemy import Connection, Row

from routers.dependencies import expdb_connection, fetch_user

router = APIRouter(prefix="/studies", tags=["studies"])


def _get_study_raise_otherwise(id_or_alias: int | str, user: User | None, expdb: Connection) -> Row:
    if isinstance(id_or_alias, int) or id_or_alias.isdigit():
        study = get_study_by_id(int(id_or_alias), expdb)
    else:
        study = get_study_by_alias(id_or_alias, expdb)

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

    return study


@router.get("/{alias_or_id}")
def get_study(
    alias_or_id: int | str,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> Study:
    study = _get_study_raise_otherwise(alias_or_id, user, expdb)
    study_data = get_study_data(study, expdb)
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
