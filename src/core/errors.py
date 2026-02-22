from enum import IntEnum


class DatasetError(IntEnum):
    NOT_FOUND = 111
    NO_ACCESS = 112
    NO_DATA_FILE = 113


class QualityError(IntEnum):
    UNKNOWN_DATASET = 361
    NO_QUALITIES = 362
    NOT_PROCESSED = 363
    PROCESSED_WITH_ERROR = 364
