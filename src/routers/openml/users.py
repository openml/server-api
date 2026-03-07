from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection

from core.errors import UserError
from database.users import User, UserGroup, delete_user, get_user_resource_count
from routers.dependencies import expdb_connection, fetch_user, userdb_connection

router = APIRouter(prefix="/users", tags=["users"])


@router.delete(
    "/{user_id}",
    summary="Delete a user account",
    description=(
        "Deletes the account of the specified user. "
        "Only the account owner or an admin may perform this action. "
        "Deletion is blocked if the user has uploaded any datasets, flows, or runs."
    ),
)
def delete_account(
    user_id: int,
    caller: Annotated[User | None, Depends(fetch_user)] = None,
    user_db: Annotated[Connection, Depends(userdb_connection)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[str, Any]:
    if caller is None:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail={"code": str(int(UserError.NO_ACCESS)), "message": "Authentication required"},
        )

    is_admin = UserGroup.ADMIN in caller.groups
    is_self = caller.user_id == user_id

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail={"code": str(int(UserError.NO_ACCESS)), "message": "No access granted"},
        )

    from sqlalchemy import text  # noqa: PLC0415

    existing = user_db.execute(
        text("SELECT 1 FROM users WHERE id = :id LIMIT 1"),
        parameters={"id": user_id},
    ).scalar()

    if existing is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail={"code": str(int(UserError.NOT_FOUND)), "message": "User not found"},
        )

    resource_count = get_user_resource_count(user_id=user_id, expdb=expdb)
    if resource_count > 0:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail={
                "code": str(int(UserError.HAS_RESOURCES)),
                "message": (
                    f"User has {resource_count} resource(s). "
                    "Remove or transfer resources before deleting the account."
                ),
            },
        )

    delete_user(user_id=user_id, connection=user_db)
    return {"user_id": user_id, "deleted": True}
