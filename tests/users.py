from enum import StrEnum

from database.users import User, UserGroup

NO_USER = None
SOME_USER = User(user_id=2, _database=None, _groups=[UserGroup.READ_WRITE])
OWNER_USER = User(user_id=16, _database=None, _groups=[UserGroup.READ_WRITE])
ADMIN_USER = User(user_id=1, _database=None, _groups=[UserGroup.ADMIN, UserGroup.READ_WRITE])


class ApiKey(StrEnum):
    ADMIN = "abc"
    SOME_USER = "normaluser"
    OWNER_USER = "normaluser2"
    INVALID = "11111111111111111111111111111111"
