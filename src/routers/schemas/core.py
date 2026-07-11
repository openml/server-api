"""Schema components used in many routers."""

from enum import StrEnum, auto
from typing import NotRequired, TypedDict

from core.types import TagString


class Visibility(StrEnum):
    """Visibility of an asset."""

    PUBLIC = auto()
    PRIVATE = auto()


class TagInfo(TypedDict):
    """Common PHP response format for tag operations."""

    id: str
    tag: NotRequired[TagString | list[TagString]]
