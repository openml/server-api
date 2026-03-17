"""All endpoints that relate to setups."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from sqlalchemy.ext.asyncio import AsyncConnection

import database.setups
from core.errors import (
    SetupNotFoundError,
    TagAlreadyExistsError,
    TagNotFoundError,
    TagNotOwnedError,
)
from database.users import User, UserGroup
from routers.dependencies import expdb_connection, fetch_user_or_raise
from routers.types import SystemString64
from schemas.setups import SetupParameters, SetupResponse

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get(path="/{setup_id}", response_model_exclude_none=True)
async def get_setup(
    setup_id: Annotated[int, Path()],
    expdb_db: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> SetupResponse:
    """Get setup by id."""
    setup = await database.setups.get(setup_id, expdb_db)
    if not setup:
        msg = f"Setup {setup_id} not found."
        raise SetupNotFoundError(msg, code=281)

    setup_parameters = await database.setups.get_parameters(setup_id, expdb_db)

    params_model = SetupParameters(
        setup_id=str(setup_id),
        flow_id=str(setup.implementation_id),
        parameter=[dict(param) for param in setup_parameters] if setup_parameters else None,
    )

    return SetupResponse(setup_parameters=params_model)


@router.post(path="/tag")
async def tag_setup(
    setup_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb_db: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> dict[str, dict[str, str | list[str]]]:
    """Add tag `tag` to setup with id `setup_id`."""
    if not await database.setups.get(setup_id, expdb_db):
        msg = f"Setup {setup_id} not found."
        raise SetupNotFoundError(msg)

    setup_tags = await database.setups.get_tags(setup_id, expdb_db)
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
    remaining_tags = [
        t.tag for t in setup_tags if t.tag.casefold() != matched_tag_row.tag.casefold()
    ]
    return {"setup_untag": {"id": str(setup_id), "tag": remaining_tags}}
