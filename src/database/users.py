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


async def get_user(
    *,
    connection: AsyncConnection,
    api_key: APIKey | None = None,
    user_id: int | None = None,
) -> User | None:
    """Fetch the full user by either api_key or user_id."""
    if (api_key is None) == (user_id is None):
        msg = "Exactly one of api_key or user_id must be provided."
        raise ValueError(msg)

    if api_key is not None:
        query = """
        SELECT id, first_name, last_name
        FROM users
        WHERE session_hash = :api_key
        LIMIT 1
        """
    else:
        query = """
        SELECT id, first_name, last_name
        FROM users
        WHERE id = :user_id
        LIMIT 1
        """

    result = await connection.execute(
        text(query),
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
    first_name: str = ""
    last_name: str = ""
    _groups: list[UserGroup] | None = None

    def __post_init__(self) -> None:
        """Convert None names to empty strings to satisfy str type."""
        if self.first_name is None:
            self.first_name = ""
        if self.last_name is None:
            self.last_name = ""

    @property
    def full_name(self) -> str:
        """Return the combined first and last name."""
        return f"{self.first_name} {self.last_name}".strip()

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
            self._groups = await get_user_groups_for(
                user_id=self.user_id,
                connection=self._database,
            )
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
