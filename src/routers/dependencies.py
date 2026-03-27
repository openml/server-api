from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import AuthenticationFailedError, AuthenticationRequiredError
from database.setup import expdb_database, user_database
from database.users import APIKey, User


async def expdb_connection() -> AsyncGenerator[AsyncConnection, None]:
    engine = expdb_database()
    async with engine.connect() as connection, connection.begin():
        yield connection


async def userdb_connection() -> AsyncGenerator[AsyncConnection, None]:
    engine = user_database()
    async with engine.connect() as connection, connection.begin():
        yield connection


async def fetch_user(
    api_key: APIKey | None = None,
    user_data: Annotated[AsyncConnection | None, Depends(userdb_connection)] = None,
) -> User | None:
    if not (api_key and user_data):
        return None

    user = await User.fetch(api_key, user_data)
    if user:
        return user
    msg = "Invalid API key provided."
    raise AuthenticationFailedError(msg)


def fetch_user_or_raise(
    user: Annotated[User | None, Depends(fetch_user)] = None,
) -> User:
    if user is None:
        msg = "No API key provided."
        raise AuthenticationRequiredError(msg)
    return user


class Pagination(BaseModel):
    offset: int = 0
    limit: int = 100
