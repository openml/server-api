from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncConnection

from database.setup import expdb_database, user_database
from database.users import APIKey, User


async def expdb_connection() -> AsyncGenerator[AsyncConnection, None]:
    engine = expdb_database()
    async with engine.connect() as connection:
        yield connection
        await connection.commit()


async def userdb_connection() -> AsyncGenerator[AsyncConnection, None]:
    engine = user_database()
    async with engine.connect() as connection:
        yield connection
        await connection.commit()


async def fetch_user(
    api_key: APIKey | None = None,
    user_data: Annotated[AsyncConnection | None, Depends(userdb_connection)] = None,
) -> User | None:
    return await User.fetch(api_key, user_data) if api_key and user_data else None


class Pagination(BaseModel):
    offset: int = 0
    limit: int = 100
