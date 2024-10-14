import pytest
from sqlalchemy import Connection

from database.users import User
from routers.dependencies import fetch_user
from tests.users import ADMIN_USER, OWNER_USER, SOME_USER, ApiKey


@pytest.mark.parametrize(
    ("api_key", "user"),
    [
        (ApiKey.ADMIN, ADMIN_USER),
        (ApiKey.OWNER_USER, OWNER_USER),
        (ApiKey.SOME_USER, SOME_USER),
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
