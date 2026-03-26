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


def nested_remove_nones(obj: Any, *, remove_empty_list: bool = False) -> Any:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, Mapping):
        cleaned: dict[Any, Any] = {}
        for key, val in obj.items():
            cleaned_val = nested_remove_nones(val, remove_empty_list=remove_empty_list)
            if cleaned_val is None:
                continue
            if remove_empty_list and cleaned_val == []:
                continue
            cleaned[key] = cleaned_val
        return cleaned
    if isinstance(obj, Iterable):
        cleaned_list: list[Any] = []
        for val in obj:
            cleaned_val = nested_remove_nones(val, remove_empty_list=remove_empty_list)
            if cleaned_val is None:
                continue
            if remove_empty_list and cleaned_val == []:
                continue
            cleaned_list.append(cleaned_val)
        return cleaned_list
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
