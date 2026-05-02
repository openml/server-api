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


async def get_user(
    *,
    connection: AsyncConnection,
    api_key: APIKey | None = None,
    user_id: int | None = None,
) -> "User | None":
    """Fetch the full user by either api_key or user_id."""
    result = await connection.execute(
        text(
            """
    SELECT id, first_name, last_name
    FROM users
    WHERE session_hash = :api_key OR id = :user_id
    LIMIT 1
    """,
        ),
        parameters={"api_key": api_key, "user_id": user_id},
    )
    row = result.one_or_none()
    if row:
        return User(
            user_id=row.id,
            first_name=row.first_name,
            last_name=row.last_name,
            _database=connection,
        )
    return None


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
    first_name: str = ""
    last_name: str = ""
    _groups: list[UserGroup] | None = None

    @property
    def full_name(self) -> str:
        """Return the combined first and last name."""
        return f"{self.first_name} {self.last_name}"

    @classmethod
    async def fetch(cls, api_key: APIKey, user_db: AsyncConnection) -> Self | None:
        user = await get_user(api_key=api_key, connection=user_db)
        if user is not None:
            return cls(
                user_id=user.user_id,
                first_name=user.first_name,
                last_name=user.last_name,
                _database=user_db,
            )
        return None

    async def get_groups(self) -> list[UserGroup]:
        if self._groups is None:
            group_ids = await get_user_groups_for(user_id=self.user_id, connection=self._database)
            self._groups = [UserGroup(group_id) for group_id in group_ids]
        return self._groups

    async def is_admin(self) -> bool:
        return UserGroup.ADMIN in await self.get_groups()
