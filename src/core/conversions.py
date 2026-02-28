from collections.abc import Iterable, Mapping, Sequence

"""Utilities for converting between string and numeric representations.

Provides functions for recursive conversion of nested data structures.
"""

from typing import Any


def _str_to_num(string: str) -> int | float | str:
    """Convert string to integer, float, or leave unchanged.

    Attempts conversion in order: integer, float, then returns original string.
    """
    if string.isdigit():
        return int(string)
    try:
        return float(string)
    except ValueError:
        return string


def nested_str_to_num(obj: Any) -> Any:
    """Recursively convert all strings in object to numbers.

    For dictionaries, only the values will be converted.
    """
    if isinstance(obj, str):
        return _str_to_num(obj)
    if isinstance(obj, Mapping):
        return {key: nested_str_to_num(val) for key, val in obj.items()}
    if isinstance(obj, Iterable):
        return [nested_str_to_num(val) for val in obj]
    return obj


def nested_num_to_str(obj: Any) -> Any:
    """Recursively convert all numbers in object to strings.

    For dictionaries, only the values will be converted.
    """
    if isinstance(obj, str):
        return obj
    if isinstance(obj, Mapping):
        return {key: nested_num_to_str(val) for key, val in obj.items()}
    if isinstance(obj, Iterable):
        return [nested_num_to_str(val) for val in obj]
    if isinstance(obj, int | float):
        return str(obj)
    return obj


def nested_remove_nones(obj: Any) -> Any:
    """Recursively remove None values from nested data structures."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, Mapping):
        return {
            key: nested_remove_nones(val)
            for key, val in obj.items()
            if val is not None and nested_remove_nones(val) is not None
        }
    if isinstance(obj, Iterable):
        return [nested_remove_nones(val) for val in obj if nested_remove_nones(val) is not None]
    return obj


def nested_remove_single_element_list(obj: Any) -> Any:
    """Recursively unwrap single-element lists in nested data structures."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, Mapping):
        return {key: nested_remove_single_element_list(val) for key, val in obj.items()}
    if isinstance(obj, Sequence):
        if len(obj) == 1:
            return nested_remove_single_element_list(obj[0])
        return [nested_remove_single_element_list(val) for val in obj]
    return obj
