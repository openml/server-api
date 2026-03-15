"""All endpoints that relate to setups."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

import database.setups
from core.errors import SetupNotFoundError, TagNotFoundError, TagNotOwnedError
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
) -> dict[str, dict[str, str | list[str]]]:
    """Remove tag `tag` from setup with id `setup_id`."""
    if not await database.setups.get(setup_id, expdb_db):
        msg = f"Setup {setup_id} not found."
        raise SetupNotFoundError(msg)

    setup_tags = await database.setups.get_tags(setup_id, expdb_db)
    matched_tag_row = next((t for t in setup_tags if t.tag.casefold() == tag.casefold()), None)

    if not matched_tag_row:
        msg = f"Setup {setup_id} does not have tag {tag!r}."
        raise TagNotFoundError(msg)

    if matched_tag_row.uploader != user.user_id and UserGroup.ADMIN not in await user.get_groups():
        msg = (
            f"You may not remove tag {tag!r} of setup {setup_id} because it was not created by you."
        )
        raise TagNotOwnedError(msg)

    await database.setups.untag(setup_id, matched_tag_row.tag, expdb_db)
    remaining_tags = [t.tag.casefold() for t in setup_tags if t != matched_tag_row]
    return {"setup_untag": {"id": str(setup_id), "tag": remaining_tags}}
