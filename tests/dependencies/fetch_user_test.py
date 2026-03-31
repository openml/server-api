import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import AuthenticationFailedError, AuthenticationRequiredError
from database.users import User
from routers.dependencies import fetch_user, fetch_user_or_raise
from tests.users import ADMIN_USER, OWNER_USER, SOME_USER, ApiKey


@pytest.mark.parametrize(
    ("api_key", "user"),
    [
        (ApiKey.ADMIN, ADMIN_USER),
        (ApiKey.OWNER_USER, OWNER_USER),
        (ApiKey.SOME_USER, SOME_USER),
    ],
)
async def test_fetch_user(api_key: str, user: User, user_test: AsyncConnection) -> None:
    db_user = await fetch_user(api_key, user_data=user_test)
    assert isinstance(db_user, User)
    assert user.user_id == db_user.user_id
    assert set(await user.get_groups()) == set(await db_user.get_groups())


async def test_fetch_user_no_key_no_user() -> None:
    assert await fetch_user(api_key=None) is None


async def test_fetch_user_invalid_key_raises(user_test: AsyncConnection) -> None:
    with pytest.raises(AuthenticationFailedError):
        await fetch_user(api_key=ApiKey.INVALID, user_data=user_test)


async def test_fetch_user_or_raise_raises_if_no_user() -> None:
    # This function calls `fetch_user` through dependency injection,
    # so it only needs to correctly handle possible output of `fetch_user`.
    with pytest.raises(AuthenticationRequiredError):
        fetch_user_or_raise(user=None)
