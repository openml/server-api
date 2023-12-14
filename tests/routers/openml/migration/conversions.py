from typing import Any


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
