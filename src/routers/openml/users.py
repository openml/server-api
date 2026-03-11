import uuid
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection, text

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
        "Deletion is blocked if the user has uploaded any owned resources."
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

    original = user_db.execute(
        text("SELECT session_hash FROM users WHERE id = :id FOR UPDATE"),
        parameters={"id": user_id},
    ).fetchone()

    if original is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail={"code": str(int(UserError.NOT_FOUND)), "message": "User not found"},
        )

    # Invalidate session while delete flow is in-progress.
    original_session_hash = original[0]
    temp_lock_hash = uuid.uuid4().hex
    user_db.execute(
        text("UPDATE users SET session_hash = :lock_hash WHERE id = :id"),
        parameters={"lock_hash": temp_lock_hash, "id": user_id},
    )
    # Persist lock hash before cross-database checks so other connections
    # cannot keep authenticating with the old session hash.
    user_db.commit()

    deletion_successful = False
    try:
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
        user_db.commit()
        deletion_successful = True
        return {"user_id": user_id, "deleted": True}
    finally:
        if not deletion_successful:
            # Restore only if we still hold our lock value.
            user_db.execute(
                text(
                    "UPDATE users SET session_hash = :hash "
                    "WHERE id = :id AND session_hash = :lock_hash",
                ),
                parameters={
                    "hash": original_session_hash,
                    "id": user_id,
                    "lock_hash": temp_lock_hash,
                },
            )
            user_db.commit()
