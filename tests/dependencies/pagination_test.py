from typing import Any

import pytest
from pydantic import ValidationError

from routers.dependencies import Pagination


def test_pagination_defaults() -> None:
    """Pagination has expected defaults when no values are provided."""
    pagination = Pagination()
    assert pagination.offset == 0
    assert pagination.limit == 100


@pytest.mark.parametrize(
    ("kwargs", "expected_field"),
    [
        ({"limit": "abc", "offset": 0}, "limit"),
        ({"limit": 5, "offset": "xyz"}, "offset"),
    ],
    ids=["bad_limit_type", "bad_offset_type"],
)
def test_pagination_invalid_type(kwargs: dict[str, Any], expected_field: str) -> None:
    """Non-integer values for limit or offset raise a ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Pagination(**kwargs)
    errors = exc_info.value.errors()
    assert any(error["loc"] == (expected_field,) for error in errors)
