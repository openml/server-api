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

    async def is_admin(self) -> bool:
        return UserGroup.ADMIN in await self.get_groups()


async def exists_by_id(*, user_id: int, connection: AsyncConnection) -> bool:
    row = await connection.execute(
        text("SELECT 1 FROM users WHERE id = :user_id LIMIT 1"),
        parameters={"user_id": user_id},
    )
    return row.one_or_none() is not None


async def has_user_references(*, user_id: int, expdb: AsyncConnection) -> bool:
    """Return ``True`` if any ``expdb`` row still references ``user_id``."""
    row = await expdb.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1 FROM dataset              WHERE uploader = :uid
                UNION ALL SELECT 1 FROM dataset_description WHERE uploader = :uid
                UNION ALL SELECT 1 FROM dataset_status      WHERE user_id  = :uid
                UNION ALL SELECT 1 FROM dataset_tag         WHERE uploader = :uid
                UNION ALL SELECT 1 FROM dataset_topic       WHERE uploader = :uid
                UNION ALL SELECT 1 FROM implementation      WHERE uploader = :uid
                UNION ALL SELECT 1 FROM implementation_tag  WHERE uploader = :uid
                UNION ALL SELECT 1 FROM `run`               WHERE uploader = :uid
                UNION ALL SELECT 1 FROM run_study           WHERE uploader = :uid
                UNION ALL SELECT 1 FROM run_tag             WHERE uploader = :uid
                UNION ALL SELECT 1 FROM setup_tag           WHERE uploader = :uid
                UNION ALL SELECT 1 FROM study               WHERE creator  = :uid
                UNION ALL SELECT 1 FROM task                WHERE creator  = :uid
                UNION ALL SELECT 1 FROM task_study          WHERE uploader = :uid
                UNION ALL SELECT 1 FROM task_tag            WHERE uploader = :uid
            ) AS has_refs
            """,
        ),
        parameters={"uid": user_id},
    )
    return bool(row.scalar_one())


async def delete_user_rows(*, user_id: int, userdb: AsyncConnection) -> None:
    """Remove group memberships then the user row (openml user database)."""
    await userdb.execute(
        text("DELETE FROM users_groups WHERE user_id = :user_id"),
        parameters={"user_id": user_id},
    )
    await userdb.execute(
        text("DELETE FROM users WHERE id = :user_id"),
        parameters={"user_id": user_id},
    )
