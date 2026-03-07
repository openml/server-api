from enum import IntEnum


class DatasetError(IntEnum):
    NOT_FOUND = 111
    NO_ACCESS = 112
    NO_DATA_FILE = 113


class UserError(IntEnum):
    NOT_FOUND = 120
    NO_ACCESS = 121
    HAS_RESOURCES = 122
