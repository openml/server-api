from typing import Annotated

from config import load_database_configuration
from pydantic import StringConstraints
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL

from database.meta import get_column_names

_database_configuration = load_database_configuration()

openml_url = URL.create(**_database_configuration["openml"])
openml = create_engine(
    openml_url,
    echo=True,
    pool_recycle=3600,
)

# Enforces str is 32 hexadecimal characters, does not check validity.
APIKey = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{32}$")]


def get_user_id_for(*, api_key: APIKey, engine: Engine = openml) -> int | None:
    columns = get_column_names(openml, "users")
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
        SELECT *
        FROM users
        WHERE session_hash = :api_key
        """,
            ),
            parameters={"api_key": api_key},
        )
    if not (user := next(row, None)):
        return None
    return int(dict(zip(columns, user, strict=True))["id"])


def get_user_groups_for(*, user_id: int, engine: Engine = openml) -> list[int]:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
        SELECT group_id
        FROM users_groups
        WHERE user_id = :user_id
        """,
            ),
            parameters={"user_id": user_id},
        )
    return [group for group, in row]
