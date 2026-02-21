from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import Connection

import database.runs
from database.users import User, UserGroup
from routers.dependencies import expdb_connection, fetch_user
from routers.types import SystemString64

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post(path="/tag")
def tag_run(
    run_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[str, dict[str, Any]]:
    if user is None:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "103", "message": "Authentication failed"},
        )
    tags = database.runs.get_tags(run_id, expdb)
    if tag.casefold() in [t.casefold() for t in tags]:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail={
                "code": "473",
                "message": "Entity already tagged by this tag.",
                "additional_information": f"id={run_id}; tag={tag}",
            },
        )
    database.runs.tag(run_id, tag, user_id=user.user_id, connection=expdb)
    return {"run_tag": {"id": str(run_id), "tag": [*tags, tag]}}


@router.post(path="/untag")
def untag_run(
    run_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[str, dict[str, Any]]:
    if user is None:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "103", "message": "Authentication failed"},
        )
    existing = database.runs.get_tag(run_id, tag, expdb)
    if existing is None:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail={
                "code": "477",
                "message": "Tag not found.",
                "additional_information": f"id={run_id}; tag={tag}",
            },
        )
    if existing.uploader != user.user_id and UserGroup.ADMIN not in user.groups:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail={
                "code": "478",
                "message": "Tag is not owned by you.",
                "additional_information": f"id={run_id}; tag={tag}",
            },
        )
    database.runs.delete_tag(run_id, tag, expdb)
    tags = database.runs.get_tags(run_id, expdb)
    return {"run_tag": {"id": str(run_id), "tag": tags}}
