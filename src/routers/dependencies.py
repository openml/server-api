from collections.abc import AsyncGenerator, AsyncIterator
from typing import Annotated

from fastapi import Depends
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import AuthenticationFailedError, AuthenticationRequiredError
from database.setup import expdb_database, user_database
from database.users import APIKey, User


async def expdb_connection() -> AsyncIterator[AsyncConnection]:
    engine = expdb_database()
    async with engine.connect() as connection, connection.begin():
        yield connection


async def userdb_connection() -> AsyncIterator[AsyncConnection]:
    engine = user_database()
    async with engine.connect() as connection, connection.begin():
        yield connection


async def fetch_user(
    api_key: APIKey | None = None,
    user_data: Annotated[AsyncConnection | None, Depends(userdb_connection)] = None,
) -> AsyncGenerator[User | None]:
    if not (api_key and user_data):
        yield None
        return

    user = await User.fetch(api_key, user_data)
    masked_key = api_key[-4:]
    if not user:
        logger.info("Authentication failed.", api_key=masked_key)
        msg = "Invalid API key provided."
        raise AuthenticationFailedError(msg)

    logger.info(
        "User {identifier} authenticated with api key ending in '{api_key}'.",
        identifier=user.user_id,
        api_key=masked_key,
    )
    with logger.contextualize(user_id=user.user_id):
        yield user


def fetch_user_or_raise(
    user: Annotated[User | None, Depends(fetch_user)] = None,
) -> User:
    if user is None:
        logger.info("Unauthenticated user tried to access endpoint that requires authentication.")
        msg = "No API key provided."
        raise AuthenticationRequiredError(msg)
    return user


class Pagination(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, gt=0, le=1000)
