"""Tests validation of custom types.

Note that for parametrized tests, it is important that the value order and
amount must be consistent to allow distribution with pytest-xdist:
https://pytest-xdist.readthedocs.io/en/latest/known-limitations.html#order-and-amount-of-test-must-be-consistent

"""

import string

import pytest
from pydantic import TypeAdapter, ValidationError

from routers.types import CasualString, Identifier, TagString

_identifier = TypeAdapter(Identifier)


def test_identifier_accepts_positive_integer() -> None:
    assert _identifier.validate_strings("1") == 1


def test_identifier_rejects_non_integer() -> None:
    with pytest.raises(ValidationError):
        _identifier.validate_strings("foo")

    with pytest.raises(ValidationError):
        _identifier.validate_strings("1.2")


def test_identifier_rejects_negative() -> None:
    with pytest.raises(ValidationError):
        _identifier.validate_strings("0")


def test_identifier_rejects_zero() -> None:
    with pytest.raises(ValidationError):
        _identifier.validate_strings("0")


_tag_string = TypeAdapter(TagString)
_valid_punctuation_tag = list("_-.")
_invalid_punctuation_tag = sorted(set(string.punctuation) - set(_valid_punctuation_tag))


def test_tag_string_pattern() -> None:
    assert _tag_string.json_schema()["pattern"] == r"^[\w\-\.]+$"


@pytest.mark.parametrize("tag", ["a", "c" * 64, "version2.0", "study-14", "study_15"])
def test_tag_string_accepts_valid(tag: str) -> None:
    assert _tag_string.validate_strings(tag) == tag


@pytest.mark.parametrize("tag", ["", " ", "c" * 65, *_invalid_punctuation_tag])
def test_tag_string_rejects_invalid(tag: str) -> None:
    with pytest.raises(ValidationError):
        _tag_string.validate_strings(tag)


_casual_string = TypeAdapter(CasualString)
_valid_punctuation_casual_string = list(set("_-.(),"))
_invalid_punctuation_casual_string = sorted(
    set(string.punctuation) - set(_valid_punctuation_casual_string)
)


def test_casual_string_pattern() -> None:
    assert _casual_string.json_schema()["pattern"] == r"^[\w\-\.\(\),]+$"


@pytest.mark.parametrize("string", ["a", "a" * 1000, "_-.(),"])
def test_casual_string_accepts_valid(string: str) -> None:
    assert _casual_string.validate_strings(string)


@pytest.mark.parametrize("string", ["", *_invalid_punctuation_casual_string])
def test_casual_string_rejects_invalid(string: str) -> None:
    with pytest.raises(ValidationError):
        _casual_string.validate_strings(string)
