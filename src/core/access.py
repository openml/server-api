from typing import Any

from database.users import APIKey, get_user_groups_for, get_user_id_for
from schemas.datasets.openml import Visibility
from sqlalchemy import Connection


def _user_has_access(
    dataset: dict[str, Any],
    connection: Connection,
    api_key: APIKey | None = None,
) -> bool:
    """Determine if user of `api_key` has the right to view `dataset`."""
    if dataset["visibility"] == Visibility.PUBLIC:
        return True
    if not api_key:
        return False

    if not (user_id := get_user_id_for(api_key=api_key, connection=connection)):
        return False

    if user_id == dataset["uploader"]:
        return True

    user_groups = get_user_groups_for(user_id=user_id, connection=connection)
    ADMIN_GROUP = 1
    return ADMIN_GROUP in user_groups
