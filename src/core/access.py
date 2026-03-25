from typing import Any

from sqlalchemy.engine import Row

from database.users import User
from schemas.datasets.openml import Visibility


async def _user_has_access(
    dataset: Row[Any],
    user: User | None = None,
) -> bool:
    """Determine if `user` has the right to view `dataset`."""
    if dataset.visibility == Visibility.PUBLIC:
        return True
    if user is None:
        return False
    if user.user_id == dataset.uploader:
        return True
    return await user.is_admin()
