from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import Connection

import database.setups
from database.users import User, UserGroup
from routers.dependencies import expdb_connection, fetch_user
from routers.types import SystemString64

router = APIRouter(prefix="/setup", tags=["setup"])


def create_authentication_failed_error() -> HTTPException:
    return HTTPException(
        status_code=HTTPStatus.PRECONDITION_FAILED,
        detail={"code": "103", "message": "Authentication failed"},
    )


@router.post(path="/untag")
def untag_setup(
    setup_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb_db: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[str, dict[str, str]]:
    if user is None:
        raise create_authentication_failed_error()

    if not database.setups.get(setup_id, expdb_db):
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "472", "message": "Entity not found."},
        )

    setup_tags = database.setups.get_tags(setup_id, expdb_db)
    matched_tag_row = next((t for t in setup_tags if t.tag.casefold() == tag.casefold()), None)

    if not matched_tag_row:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "475", "message": "Tag not found."},
        )

    if matched_tag_row.uploader != user.user_id and UserGroup.ADMIN not in user.groups:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "476", "message": "Tag is not owned by you"},
        )

    database.setups.untag(setup_id, matched_tag_row.tag, expdb_db)

    return {"setup_untag": {"id": str(setup_id)}}
