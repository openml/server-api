import dataclasses
from enum import IntEnum
from typing import Annotated, Self

from pydantic import StringConstraints
from sqlalchemy import Connection, text

from config import load_configuration

# Enforces str is 32 hexadecimal characters, does not check validity.
# If `allow_test_api_keys` is set, the key may also be one of `normaluser`,
# `normaluser2`, or `abc` (admin).
api_key_pattern = r"^[0-9a-fA-F]{32}$"
if load_configuration()["development"].get("allow_test_api_keys"):
    api_key_pattern = r"^([0-9a-fA-F]{32}|normaluser|normaluser2|abc)$"

APIKey = Annotated[
    str,
    StringConstraints(pattern=api_key_pattern),
]


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


def get_user_resource_count(*, user_id: int, expdb: Connection) -> int:
    """Return the total number of datasets, flows, and runs owned by the user."""
    dataset_count = expdb.execute(
        text("SELECT COUNT(*) FROM dataset WHERE uploader = :user_id"),
        parameters={"user_id": user_id},
    ).scalar() or 0
    flow_count = expdb.execute(
        text("SELECT COUNT(*) FROM implementation WHERE uploader = :user_id"),
        parameters={"user_id": user_id},
    ).scalar() or 0
    run_count = expdb.execute(
        text("SELECT COUNT(*) FROM run WHERE uploader = :user_id"),
        parameters={"user_id": user_id},
    ).scalar() or 0

    study_count = expdb.execute(
        text("SELECT COUNT(*) FROM study WHERE creator = :user_id"),
        parameters={"user_id": user_id},
    ).scalar() or 0
    task_study_count = expdb.execute(
        text("SELECT COUNT(*) FROM task_study WHERE uploader = :user_id"),
        parameters={"user_id": user_id},
    ).scalar() or 0
    run_study_count = expdb.execute(
        text("SELECT COUNT(*) FROM run_study WHERE uploader = :user_id"),
        parameters={"user_id": user_id},
    ).scalar() or 0
    dataset_tag_count = expdb.execute(
        text("SELECT COUNT(*) FROM dataset_tag WHERE uploader = :user_id"),
        parameters={"user_id": user_id},
    ).scalar() or 0

    return int(
        dataset_count
        + flow_count
        + run_count
        + study_count
        + task_study_count
        + run_study_count
        + dataset_tag_count,
    )


def delete_user(*, user_id: int, connection: Connection) -> None:
    """Remove the user and their group memberships from the user database."""
    with connection.begin_nested() as transaction:
        try:
            connection.execute(
                text("DELETE FROM users_groups WHERE user_id = :user_id"),
                parameters={"user_id": user_id},
            )
            connection.execute(
                text("DELETE FROM users WHERE id = :user_id"),
                parameters={"user_id": user_id},
            )
        except Exception:
            transaction.rollback()
            raise
