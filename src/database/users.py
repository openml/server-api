import dataclasses
from enum import IntEnum
from typing import Annotated, Self

from pydantic import StringConstraints
from sqlalchemy import Connection, text

# Enforces str is 32 hexadecimal characters, does not check validity.
APIKey = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{32}$")]


class UserGroup(IntEnum):
    ADMIN = (1,)
    READ_WRITE = (2,)
    READ_ONLY = (3,)


def get_user_id_for(*, api_key: APIKey, connection: Connection) -> int | None:
    user = connection.execute(
        text(
            """
    SELECT *
    FROM users
    WHERE session_hash = :api_key
    """,
        ),
        parameters={"api_key": api_key},
    ).one_or_none()
    return user.id if user else None


def get_user_groups_for(*, user_id: int, connection: Connection) -> list[UserGroup]:
    row = connection.execute(
        text(
            """
    SELECT group_id
    FROM users_groups
    WHERE user_id = :user_id
    """,
        ),
        parameters={"user_id": user_id},
    )
    return [UserGroup(group) for (group,) in row]


@dataclasses.dataclass
class User:
    user_id: int
    _database: Connection
    _groups: list[UserGroup] | None = None

    @classmethod
    def fetch(cls, api_key: APIKey, user_db: Connection) -> Self | None:
        if user_id := get_user_id_for(api_key=api_key, connection=user_db):
            return cls(user_id, _database=user_db)
        return None

    @property
    def groups(self) -> list[UserGroup]:
        if self._groups is None:
            groups = get_user_groups_for(user_id=self.user_id, connection=self._database)
            self._groups = [UserGroup(group_id) for group_id in groups]
        return self._groups
