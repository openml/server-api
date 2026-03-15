import dataclasses
from enum import IntEnum
from typing import Annotated, Self

from pydantic import StringConstraints
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from config import load_configuration

# If `allow_test_api_keys` is set, the key may also be one of `normaluser`,
# `normaluser2`, or `abc` (admin).
api_key_pattern = r"^[0-9a-fA-F]{32}$"
if load_configuration().get("development", {}).get("allow_test_api_keys"):
    api_key_pattern = r"^([0-9a-fA-F]{32}|normaluser|normaluser2|abc)$"

APIKey = Annotated[
    str,
    StringConstraints(pattern=api_key_pattern),
]


class UserGroup(IntEnum):
    ADMIN = (1,)
    READ_WRITE = (2,)
    READ_ONLY = (3,)


async def get_user_id_for(*, api_key: APIKey, connection: AsyncConnection) -> int | None:
    row = await connection.execute(
        text(
            """
    SELECT *
    FROM users
    WHERE session_hash = :api_key
    """,
        ),
        parameters={"api_key": api_key},
    )
    user = row.one_or_none()
    return user.id if user else None


async def get_user_groups_for(*, user_id: int, connection: AsyncConnection) -> list[int]:
    row = await connection.execute(
        text(
            """
    SELECT group_id
    FROM users_groups
    WHERE user_id = :user_id
    """,
        ),
        parameters={"user_id": user_id},
    )
    rows = row.all()
    return [group for (group,) in rows]


@dataclasses.dataclass
class User:
    user_id: int
    _database: AsyncConnection
    _groups: list[UserGroup] | None = None

    @classmethod
    async def fetch(cls, api_key: APIKey, user_db: AsyncConnection) -> Self | None:
        if (user_id := await get_user_id_for(api_key=api_key, connection=user_db)) is not None:
            return cls(user_id, _database=user_db)
        return None

    async def get_groups(self) -> list[UserGroup]:
        if self._groups is None:
            group_ids = await get_user_groups_for(user_id=self.user_id, connection=self._database)
            self._groups = [UserGroup(group_id) for group_id in group_ids]
        return self._groups


async def get_user_resource_count(*, user_id: int, expdb: AsyncConnection) -> int:
    """Return the total number of datasets, flows, and runs owned by the user."""
    dataset_count = (
        (
            await expdb.execute(
                text("SELECT COUNT(*) FROM dataset WHERE uploader = :user_id"),
                parameters={"user_id": user_id},
            )
        ).scalar()
        or 0
    )
    flow_count = (
        (
            await expdb.execute(
                text("SELECT COUNT(*) FROM implementation WHERE uploader = :user_id"),
                parameters={"user_id": user_id},
            )
        ).scalar()
        or 0
    )
    run_count = (
        (
            await expdb.execute(
                text("SELECT COUNT(*) FROM run WHERE uploader = :user_id"),
                parameters={"user_id": user_id},
            )
        ).scalar()
        or 0
    )

    study_count = (
        (
            await expdb.execute(
                text("SELECT COUNT(*) FROM study WHERE creator = :user_id"),
                parameters={"user_id": user_id},
            )
        ).scalar()
        or 0
    )
    task_study_count = (
        (
            await expdb.execute(
                text("SELECT COUNT(*) FROM task_study WHERE uploader = :user_id"),
                parameters={"user_id": user_id},
            )
        ).scalar()
        or 0
    )
    run_study_count = (
        (
            await expdb.execute(
                text("SELECT COUNT(*) FROM run_study WHERE uploader = :user_id"),
                parameters={"user_id": user_id},
            )
        ).scalar()
        or 0
    )
    dataset_tag_count = (
        (
            await expdb.execute(
                text("SELECT COUNT(*) FROM dataset_tag WHERE uploader = :user_id"),
                parameters={"user_id": user_id},
            )
        ).scalar()
        or 0
    )

    return int(
        dataset_count
        + flow_count
        + run_count
        + study_count
        + task_study_count
        + run_study_count
        + dataset_tag_count,
    )


async def delete_user(*, user_id: int, connection: AsyncConnection) -> None:
    """Remove the user and their group memberships from the user database."""
    async with connection.begin_nested():
        await connection.execute(
            text("DELETE FROM users_groups WHERE user_id = :user_id"),
            parameters={"user_id": user_id},
        )
        await connection.execute(
            text("DELETE FROM users WHERE id = :user_id"),
            parameters={"user_id": user_id},
        )
