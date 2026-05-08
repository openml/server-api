import dataclasses
import functools
import re
from enum import IntEnum
from typing import TYPE_CHECKING, Annotated, Self

from pydantic import AfterValidator
from sqlalchemy import text

from config import get_config
from routers.types import Identifier

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection


api_key_pattern = re.compile(r"^[0-9a-fA-F]{32}$")
# The test database currently contains some non-standard API keys
api_key_pattern_with_test = re.compile(r"^([0-9a-fA-F]{32}|normaluser|normaluser2|abc)$")


@functools.cache
def is_valid_api_key(key: str) -> str:
    """Raise ValueError if key is not valid, return key otherwise."""
    pattern = api_key_pattern
    if get_config().development.allow_test_api_keys:
        pattern = api_key_pattern_with_test
    if not pattern.match(key):
        msg = f"API key {key!r} format is not valid."
        raise ValueError(msg)
    return key


APIKey = Annotated[
    str,
    AfterValidator(is_valid_api_key),
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


async def get_user_groups_for(
    *,
    user_id: Identifier,
    connection: AsyncConnection,
) -> list[UserGroup]:
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
    return [UserGroup(group) for (group,) in rows]


@dataclasses.dataclass
class User:
    user_id: Identifier
    _database: AsyncConnection
    _groups: list[UserGroup] | None = None

    @classmethod
    async def fetch(cls, api_key: APIKey, user_db: AsyncConnection) -> Self | None:
        if (user_id := await get_user_id_for(api_key=api_key, connection=user_db)) is not None:
            return cls(user_id, _database=user_db)
        return None

    async def get_groups(self) -> list[UserGroup]:
        if self._groups is None:
            self._groups = await get_user_groups_for(
                user_id=self.user_id,
                connection=self._database,
            )
        return self._groups

    async def is_admin(self) -> bool:
        return UserGroup.ADMIN in await self.get_groups()
