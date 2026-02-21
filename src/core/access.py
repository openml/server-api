from sqlalchemy.engine import Row

from database.users import User, UserGroup
from schemas.datasets.openml import Visibility


async def _user_has_access(
    dataset: Row,
    user: User | None = None,
) -> bool:
    """Determine if `user` has the right to view `dataset`."""
    is_public = dataset.visibility == Visibility.PUBLIC
    if is_public:
        return True
    if user is None:
        return False
    if user.user_id == dataset.uploader:
        return True
    groups = await user.get_groups()
    return UserGroup.ADMIN in groups
