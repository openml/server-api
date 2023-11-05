from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine

from database.setup import user_database
from database.users import APIKey, User


def fetch_user(
        api_key: APIKey | None = None,
        user_data: Annotated[Engine, Depends(user_database)] = None,
) -> User | None:
    return User.fetch(api_key, user_data) if api_key else None
