from typing import Any

from sqlalchemy.engine import Row

from database.users import User, UserGroup
from schemas.datasets.openml import Visibility


async def _user_has_access(
    dataset: Row[Any],
    user: User | None = None,
) -> bool:
    """Determine if `user` has the right to view `dataset`."""
    is_public = dataset.visibility == Visibility.PUBLIC
    if is_public:
        return True
    if user is None:
        return False
    user_groups = await user.get_groups()
    return user.user_id == dataset.uploader or UserGroup.ADMIN in user_groups
