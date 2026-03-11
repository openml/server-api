"""All endpoints that relate to setups."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncConnection

import database.setups
from database.users import User, UserGroup
from routers.dependencies import expdb_connection, fetch_user_or_raise
from routers.types import SystemString64

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post(path="/untag")
async def untag_setup(
    setup_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb_db: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> dict[str, dict[str, str]]:
    """Remove tag `tag` from setup with id `setup_id`."""
    if not await database.setups.get(setup_id, expdb_db):
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "472", "message": "Entity not found."},
        )

    setup_tags = await database.setups.get_tags(setup_id, expdb_db)
    matched_tag_row = next((t for t in setup_tags if t.tag.casefold() == tag.casefold()), None)

    if not matched_tag_row:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "475", "message": "Tag not found."},
        )

    if matched_tag_row.uploader != user.user_id and UserGroup.ADMIN not in await user.get_groups():
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "476", "message": "Tag is not owned by you"},
        )

    await database.setups.untag(setup_id, matched_tag_row.tag, expdb_db)

    return {"setup_untag": {"id": str(setup_id)}}
