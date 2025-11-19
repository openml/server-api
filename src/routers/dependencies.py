from typing import Annotated

from fastapi import Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import Connection

from database.setup import expdb_database, user_database
from database.users import APIKey, User

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


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
    api_key: Annotated[APIKey | None, Depends(api_key_header)] = None,
    user_data: Annotated[Connection, Depends(userdb_connection)] = None,
) -> User | None:
    return User.fetch(api_key, user_data) if api_key else None


class Pagination(BaseModel):
    offset: int = 0
    limit: int = 100
