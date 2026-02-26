from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import Connection

import database.setups
from database.users import User, UserGroup
from routers.dependencies import expdb_connection, fetch_user
from routers.types import SystemString64

router = APIRouter(prefix="/setup", tags=["setups"])


def create_authentication_failed_error() -> HTTPException:
    return HTTPException(
        status_code=HTTPStatus.PRECONDITION_FAILED,
        detail={"code": "103", "message": "Authentication failed"},
    )


def create_tag_exists_error(setup_id: int, tag: str) -> HTTPException:
    return HTTPException(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail={
            "code": "473",
            "message": "Entity already tagged by this tag.",
            "additional_information": f"id={setup_id}; tag={tag}",
        },
    )


@router.post("/tag")
def tag_setup(
    setup_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb_db: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[str, dict[str, Any]]:
    # 1. AUTHENTICATE FIRST
    if user is None:
        raise create_authentication_failed_error()

    # 2. VERIFY EXISTENCE
    setup = database.setups.get(setup_id, expdb_db)
    if not setup:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Setup not found")

    # 3. VERIFY OWNERSHIP / PERMISSIONS
    # (Fixes the crash by not looking for a Dataset 'visibility' column)
    is_admin = UserGroup.ADMIN in user.groups
    is_owner = getattr(setup, "uploader", None) == user.user_id

    if not (is_admin or is_owner):
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="No access granted")

    # 4. CHECK IF TAG EXISTS
    tags = database.setups.get_tags_for(setup_id, expdb_db)
    if tag.casefold() in [t.casefold() for t in tags]:
        raise create_tag_exists_error(setup_id, tag)

    # 5. APPLY THE TAG
    database.setups.tag(setup_id, tag, user_id=user.user_id, connection=expdb_db)

    return {
        "setup_tag": {"id": str(setup_id), "tag": [*tags, tag]},
    }
