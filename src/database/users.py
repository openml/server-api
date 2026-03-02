import dataclasses
from enum import IntEnum
from typing import Annotated, Self

from pydantic import StringConstraints
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

# Enforces str is 32 hexadecimal characters, does not check validity.
APIKey = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{32}$")]


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
