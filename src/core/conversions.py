from typing import Any


def _str_to_num(string: str) -> int | float | str:
    """Tries to convert the string to integer, otherwise float, otherwise returns the input."""
    if string.isdigit():
        return int(string)
    try:
        return float(string)
    except ValueError:
        return string


def nested_str_to_num(obj: Any) -> Any:
    """Recursively tries to convert all strings in the object to numbers.
    For dictionaries, only the values will be converted."""
    if isinstance(obj, dict):
        return {key: nested_str_to_num(val) for key, val in obj.items()}
    if isinstance(obj, list):
        return [nested_str_to_num(val) for val in obj]
    if isinstance(obj, str):
        return _str_to_num(obj)
    return obj


def nested_int_to_str(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: nested_int_to_str(val) for key, val in obj.items()}
    if isinstance(obj, list):
        return [nested_int_to_str(val) for val in obj]
    if isinstance(obj, int):
        return str(obj)
    return obj


def nested_remove_nones(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            key: nested_remove_nones(val)
            for key, val in obj.items()
            if val is not None and nested_remove_nones(val) is not None
        }
    if isinstance(obj, list):
        return [nested_remove_nones(val) for val in obj if nested_remove_nones(val) is not None]
    return obj


def nested_remove_single_element_list(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: nested_remove_single_element_list(val) for key, val in obj.items()}
    if isinstance(obj, list):
        if len(obj) == 1:
            return nested_remove_single_element_list(obj[0])
        return [nested_remove_single_element_list(val) for val in obj]
    return obj
