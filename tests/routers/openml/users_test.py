import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

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
@pytest.mark.asyncio
async def test_fetch_user(api_key: str, user: User, user_test: AsyncConnection) -> None:
    db_user = await fetch_user(api_key, user_data=user_test)
    assert db_user is not None
    assert user.user_id == db_user.user_id
    user_groups = await user.get_groups()
    db_user_groups = await db_user.get_groups()
    assert set(user_groups) == set(db_user_groups)


@pytest.mark.asyncio
async def test_fetch_user_invalid_key_returns_none(user_test: AsyncConnection) -> None:
    assert await fetch_user(api_key=None, user_data=user_test) is None
    invalid_key = "f" * 32
    assert await fetch_user(api_key=invalid_key, user_data=user_test) is None
