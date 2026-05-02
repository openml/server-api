from typing import Callable
from sqlalchemy.exc import IntegrityError

_FOREIGN_KEY_CONSTRAINT_FAILED = 1452
_DUPLICATE_ENTRY = 1062


class ForeignKeyConstraintError(Exception):
    def __init__(self, msg):
        self.msg = msg


class DuplicatePrimaryKeyError(Exception):
    def __init__(self, msg):
        self.msg = msg


async def tag_entity(tag_function: Callable) -> None:
    try:
        await tag_function()
    except IntegrityError as e:
        code, msg = e.orig.args
        if code == _FOREIGN_KEY_CONSTRAINT_FAILED:
            raise ForeignKeyConstraintError(msg) from e
        if code == _DUPLICATE_ENTRY:
            raise DuplicatePrimaryKeyError(msg) from e
        raise
