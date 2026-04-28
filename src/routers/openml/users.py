"""User account HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

import database.users
from core.errors import AccountHasResourcesError, ForbiddenError, UserNotFoundError
from database.users import User
from routers.dependencies import expdb_connection, fetch_user_or_raise, userdb_connection

_ACCOUNT_HAS_RESOURCES_MSG = (
    "Cannot delete this account while records still reference the user "
    "(datasets, flows, runs, studies, tags, etc.). Remove or transfer them first."
)

router = APIRouter(prefix="/users", tags=["users"])


@router.delete(
    "/{user_id}",
    responses={
        204: {"description": "User account deleted."},
        401: {"description": "Authentication failed or missing."},
        403: {"description": "Not allowed to delete this account."},
        404: {"description": "User id not found."},
        409: {"description": "User still has datasets, flows, runs, or studies."},
    },
)
async def delete_user_account(
    user_id: Annotated[int, Path(description="Numeric user id to delete.", gt=0)],
    current_user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
    userdb: Annotated[AsyncConnection, Depends(userdb_connection)],
) -> Response:
    """Delete the user account if they have no associated resources.

    The account to be deleted must not have associated resources (such as
    datasets, tasks, or tags). Users may only delete their own account.
    Administrators may delete any account that satisfies the no-resources rule.
    """
    if current_user.user_id != user_id and not await current_user.is_admin():
        msg = "You may only delete your own user account."
        raise ForbiddenError(msg)

    if not await database.users.exists_by_id(user_id=user_id, connection=userdb):
        msg = f"User {user_id} not found."
        raise UserNotFoundError(msg)

    if await database.users.has_user_references(user_id=user_id, expdb=expdb):
        raise AccountHasResourcesError(_ACCOUNT_HAS_RESOURCES_MSG)

    try:
        await database.users.delete_user_rows(user_id=user_id, userdb=userdb)
    except IntegrityError as exc:
        logger.error(
            "Delete of user {user_id} failed with integrity error after pre-check.",
            user_id=user_id,
        )
        raise AccountHasResourcesError(_ACCOUNT_HAS_RESOURCES_MSG) from exc

    logger.info("User account {user_id} was removed.", user_id=user_id)
    return Response(status_code=204)
