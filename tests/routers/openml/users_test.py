from enum import StrEnum

import pytest
from sqlalchemy import Connection

from database.users import User, UserGroup
from routers.dependencies import fetch_user

NO_USER = None
SOME_USER = User(user_id=2, _database=None, _groups=[UserGroup.READ_WRITE])
OWNER_USER = User(user_id=16, _database=None, _groups=[UserGroup.READ_WRITE])
ADMIN_USER = User(user_id=1, _database=None, _groups=[UserGroup.ADMIN, UserGroup.READ_WRITE])


class ApiKey(StrEnum):
    ADMIN: str = "AD000000000000000000000000000000"
    REGULAR_USER: str = "00000000000000000000000000000000"
    OWNER_USER: str = "DA1A0000000000000000000000000000"
    INVALID: str = "11111111111111111111111111111111"


@pytest.mark.parametrize(
    ("api_key", "user"),
    [
        (ApiKey.ADMIN, ADMIN_USER),
        (ApiKey.OWNER_USER, OWNER_USER),
        (ApiKey.REGULAR_USER, SOME_USER),
    ],
)
def test_fetch_user(api_key: str, user: User, user_test: Connection) -> None:
    db_user = fetch_user(api_key, user_data=user_test)
    assert db_user is not None
    assert user.user_id == db_user.user_id
    assert user.groups == db_user.groups


def test_fetch_user_invalid_key_returns_none(user_test: Connection) -> None:
    assert fetch_user(api_key=None, user_data=user_test) is None
    invalid_key = "f" * 32
    assert fetch_user(api_key=invalid_key, user_data=user_test) is None
