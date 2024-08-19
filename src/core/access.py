from sqlalchemy.engine import Row

from database.users import User, UserGroup
from schemas.datasets.openml import Visibility


def _user_has_access(
    dataset: Row,
    user: User | None = None,
) -> bool:
    """Determine if `user` has the right to view `dataset`."""
    is_public = dataset.visibility == Visibility.PUBLIC
    return is_public or (
        user is not None and (user.user_id == dataset.uploader or UserGroup.ADMIN in user.groups)
    )
