"""Utilities for formatting and converting text data."""


def str_to_bool(string: str) -> bool:
    if string.casefold() in ["true", "1", "yes", "y"]:
        return True
    if string.casefold() in ["false", "0", "no", "n"]:
        return False
    msg = f"Could not parse {string=} as bool."
    raise ValueError(msg)


def csv_as_list(text: str | None, *, unquote_items: bool = True) -> list[str]:
    """Return comma-separated values in `text` as list, optionally remove quotes."""
    if not text:
        return []
    chars_to_strip = "'\"\t " if unquote_items else "\t "
    return [item.strip(chars_to_strip) for item in text.split(",")]
