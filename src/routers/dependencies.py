from typing import Annotated

from database.setup import expdb_database, user_database
from database.users import APIKey, User
from fastapi import Depends
from sqlalchemy import Connection


def fetch_user(
    api_key: APIKey | None = None,
    user_data: Annotated[Connection, Depends(user_database)] = None,
) -> User | None:
    return User.fetch(api_key, user_data) if api_key else None


def expdb_connection() -> Connection:
    engine = expdb_database()
    with engine.connect() as connection:
        yield connection


def userdb_connection() -> Connection:
    engine = user_database()
    with engine.connect() as connection:
        yield connection
