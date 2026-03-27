import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


def _str_to_num(string: str) -> int | float | str:
    """Try to convert the string to integer, otherwise float, otherwise returns the input."""
    if string.isdigit():
        return int(string)
    try:
        f = float(string)
        if math.isnan(f) or math.isinf(f):
            return string
    except ValueError:
        return string
    else:
        return f


def nested_str_to_num(obj: Any) -> Any:
    """Recursively try to convert all strings in the object to numbers.

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
    """Recursively try to convert all numbers in the object to strings.

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


def nested_remove_values(obj: Any, *, values: list[Any] | None = None) -> Any:
    if values is None:
        values = [None]

    if isinstance(obj, str):
        return obj
    if isinstance(obj, Mapping):
        return {
            key: nested_remove_values(val, values=values)
            for key, val in obj.items()
            if nested_remove_values(val, values=values) not in values
        }
    if isinstance(obj, Iterable):
        return [
            nested_remove_values(val, values=values)
            for val in obj
            if nested_remove_values(val, values=values) not in values
        ]
    return obj


def nested_remove_single_element_list(obj: Any) -> Any:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, Mapping):
        return {key: nested_remove_single_element_list(val) for key, val in obj.items()}
    if isinstance(obj, Sequence):
        if len(obj) == 1:
            return nested_remove_single_element_list(obj[0])
        return [nested_remove_single_element_list(val) for val in obj]
    return obj
