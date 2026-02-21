from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncConnection

from database.setup import expdb_database, user_database
from database.users import APIKey, User


async def expdb_connection() -> AsyncConnection:
    engine = expdb_database()
    async with engine.connect() as connection:
        yield connection
        await connection.commit()


async def userdb_connection() -> AsyncConnection:
    engine = user_database()
    async with engine.connect() as connection:
        yield connection
        await connection.commit()


async def fetch_user(
    api_key: APIKey | None = None,
    user_data: Annotated[AsyncConnection, Depends(userdb_connection)] = None,
) -> User | None:
    return await User.fetch(api_key, user_data) if api_key else None


class Pagination(BaseModel):
    offset: int = 0
    limit: int = 100
