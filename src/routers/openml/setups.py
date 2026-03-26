"""All endpoints that relate to setups."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

import database.setups
from core.errors import (
    SetupNotFoundError,
    TagAlreadyExistsError,
    TagNotFoundError,
    TagNotOwnedError,
)
from database.users import User
from routers.dependencies import expdb_connection, fetch_user_or_raise
from routers.types import SystemString64

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post(path="/tag")
async def tag_setup(
    setup_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb_db: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> dict[str, dict[str, str | list[str]]]:
    """Add tag `tag` to setup with id `setup_id`."""
    setup, setup_tags = await asyncio.gather(
        database.setups.get(setup_id, expdb_db),
        database.setups.get_tags(setup_id, expdb_db),
    )
    if not setup:
        msg = f"Setup {setup_id} not found."
        raise SetupNotFoundError(msg)
    matched_tag_row = next((t for t in setup_tags if t.tag.casefold() == tag.casefold()), None)

    if matched_tag_row:
        msg = f"Setup {setup_id} already has tag {tag!r}."
        raise TagAlreadyExistsError(msg)

    await database.setups.tag(setup_id, tag, user.user_id, expdb_db)
    all_tags = [t.tag for t in setup_tags] + [tag]
    return {"setup_tag": {"id": str(setup_id), "tag": all_tags}}


@router.post(path="/untag")
async def untag_setup(
    setup_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb_db: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> dict[str, dict[str, str | list[str]]]:
    """Remove tag `tag` from setup with id `setup_id`."""
    setup, setup_tags = await asyncio.gather(
        database.setups.get(setup_id, expdb_db),
        database.setups.get_tags(setup_id, expdb_db),
    )
    if not setup:
        msg = f"Setup {setup_id} not found."
        raise SetupNotFoundError(msg)
    matched_tag_row = next((t for t in setup_tags if t.tag.casefold() == tag.casefold()), None)

    if not matched_tag_row:
        msg = f"Setup {setup_id} does not have tag {tag!r}."
        raise TagNotFoundError(msg)

    if matched_tag_row.uploader != user.user_id and not await user.is_admin():
        msg = (
            f"You may not remove tag {tag!r} of setup {setup_id} because it was not created by you."
        )
        raise TagNotOwnedError(msg)

    await database.setups.untag(setup_id, matched_tag_row.tag, expdb_db)
    remaining_tags = [
        t.tag for t in setup_tags if t.tag.casefold() != matched_tag_row.tag.casefold()
    ]
    return {"setup_untag": {"id": str(setup_id), "tag": remaining_tags}}
