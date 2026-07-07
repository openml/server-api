from enum import StrEnum, auto
from typing import NotRequired, TypedDict

from core.types import TagString


class Visibility(StrEnum):
    PUBLIC = auto()
    PRIVATE = auto()


class TagInfo(TypedDict):
    """Common PHP response format for tag operations."""

    id: str
    tag: NotRequired[TagString | list[TagString]]
