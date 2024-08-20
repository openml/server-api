from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy import Connection

from database.setup import expdb_database, user_database
from database.users import APIKey, User


def expdb_connection() -> Connection:
    engine = expdb_database()
    with engine.connect() as connection:
        yield connection
        connection.commit()


def userdb_connection() -> Connection:
    engine = user_database()
    with engine.connect() as connection:
        yield connection
        connection.commit()


def fetch_user(
    api_key: APIKey | None = None,
    user_data: Annotated[Connection, Depends(userdb_connection)] = None,
) -> User | None:
    return User.fetch(api_key, user_data) if api_key else None


class Pagination(BaseModel):
    offset: int = 0
    limit: int = 100
