from pydantic import ConstrainedStr
from sqlalchemy import create_engine, text

from database.meta import get_column_names

openml = create_engine(
    "mysql://root:ok@127.0.0.1:3306/openml",
    echo=True,
    pool_recycle=3600,
)


class APIKey(ConstrainedStr):
    """Enforces str is 32 hexadecimal characters, does not check validity."""

    regex = r"^[0-9a-fA-F]{32}$"


def get_user_id_for(*, api_key: APIKey) -> int | None:
    columns = get_column_names(openml, "users")
    with openml.connect() as conn:
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


def get_user_groups_for(*, user_id: int) -> list[int]:
    with openml.connect() as conn:
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
