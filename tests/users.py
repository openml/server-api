from enum import StrEnum

from database.users import User, UserGroup

NO_USER = None
SOME_USER = User(user_id=2, _database=None, _groups=[UserGroup.READ_WRITE])
OWNER_USER = User(user_id=3229, _database=None, _groups=[UserGroup.READ_WRITE])
ADMIN_USER = User(user_id=1159, _database=None, _groups=[UserGroup.ADMIN, UserGroup.READ_WRITE])


class ApiKey(StrEnum):
    ADMIN = "abc"
    SOME_USER = "normaluser2"
    OWNER_USER = "normaluser"
    DATASET_130_OWNER = "DA1A0000000000000000000000000000"
    INVALID = "11111111111111111111111111111111"
