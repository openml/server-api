"""Defines endpoints relating to Setups."""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Body, Depends, Path
from loguru import logger

import database.setups
from core.errors import (
    SetupNotFoundError,
    TagAlreadyExistsError,
    TagNotFoundError,
    TagNotOwnedError,
)
from core.types import Identifier, TagString
from database.exceptions import DuplicatePrimaryKeyError, ForeignKeyConstraintError
from database.users import User
from routers.dependencies import expdb_connection, expdb_session, fetch_user_or_raise
from routers.schemas.setups import SetupParameters, SetupResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get(path="/{setup_id}", response_model_exclude_none=True)
async def get_setup(
    setup_id: Annotated[Identifier, Path()],
    expdb_db: Annotated[AsyncConnection, Depends(expdb_connection)],
    expdb_session: Annotated[AsyncSession, Depends(expdb_session)],
) -> SetupResponse:
    """Get setup by id."""
    setup = await database.setups.get(setup_id, expdb_session)
    if not setup:
        msg = f"Setup {setup_id} not found."
        raise SetupNotFoundError(msg, code=281)

    setup_parameters = await database.setups.get_parameters(setup_id, expdb_db)

    params_model = SetupParameters(
        setup_id=setup_id,
        flow_id=setup.flow_id,
        parameter=setup_parameters or None,
    )

    return SetupResponse(setup_parameters=params_model)


@router.post(path="/tag")
async def tag_setup(
    setup_id: Annotated[Identifier, Body()],
    tag: Annotated[TagString, Body()],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb_session: Annotated[AsyncSession, Depends(expdb_session)],
) -> dict[str, dict[str, str | list[str]]]:
    """Add a tag to the setup, this tag is publicly visible to all users."""
    try:
        await database.setups.tag(setup_id, tag, user.user_id, expdb_session)
    except ForeignKeyConstraintError:
        msg = f"Setup {setup_id} not found."
        raise SetupNotFoundError(msg, code=472) from None
    except DuplicatePrimaryKeyError:
        msg = f"Setup {setup_id} already tagged with {tag!r}."
        raise TagAlreadyExistsError(msg) from None

    logger.info("Setup {setup_id} tagged '{tag}'.", setup_id=setup_id, tag=tag)
    all_tag_rows = await database.setups.get_tags(setup_id, expdb_session)
    all_tags = [t.tag for t in all_tag_rows]

    return {"setup_tag": {"id": str(setup_id), "tag": all_tags}}


@router.post(path="/untag")
async def untag_setup(
    setup_id: Annotated[Identifier, Body()],
    tag: Annotated[TagString, Body()],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb_session: Annotated[AsyncSession, Depends(expdb_session)],
) -> dict[str, dict[str, str | list[str]]]:
    """Remove tag `tag` from setup with id `setup_id`."""
    # Setups don't really have an owner, they are associated with runs.
    # So only the tagger or admins can remove the tag.
    tag_orm = await database.setups.get_tag(setup_id, tag, expdb_session)
    if not tag_orm:
        setup = await database.setups.get(setup_id, expdb_session)
        if not setup:
            msg = f"Setup {setup_id} not found."
            raise SetupNotFoundError(msg)
        msg = f"Setup {setup_id} does not have tag {tag!r}."
        raise TagNotFoundError(msg)

    if tag_orm.uploader_id != user.user_id and not await user.is_admin():
        msg = (
            f"You may not remove tag {tag!r} of setup {setup_id} because it was not created by you."
        )
        logger.warning(
            "User attempted to remove tag '{tag}' from setup {setup_id}.",
            setup_id=setup_id,
            tag=tag,
        )
        raise TagNotOwnedError(msg)

    await database.setups.delete_tag(tag_orm, expdb_session)
    logger.info("Setup {setup_id} had tag '{tag}' removed.", setup_id=setup_id, tag=tag)
    remaining_tags = [t.tag for t in await database.setups.get_tags(setup_id, expdb_session)]
    return {"setup_untag": {"id": str(setup_id), "tag": remaining_tags}}
