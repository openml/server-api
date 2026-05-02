"""Defines exceptions of the database layer."""

_FOREIGN_KEY_CONSTRAINT_FAILED = 1452
_DUPLICATE_ENTRY = 1062


class ForeignKeyConstraintError(Exception):
    """Foreign key constraint violated."""

    def __init__(self, msg: str) -> None:
        """Initialize the error with a message `msg`."""
        super().__init__()
        self.msg: str = msg


class DuplicatePrimaryKeyError(Exception):
    """Primary key already present."""

    def __init__(self, msg: str) -> None:
        """Initialize the error with a message `msg`."""
        super().__init__()
        self.msg: str = msg
