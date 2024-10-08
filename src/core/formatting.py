import html

from sqlalchemy.engine import Row

from config import load_configuration
from core.errors import DatasetError
from schemas.datasets.openml import DatasetFileFormat


def _str_to_bool(string: str) -> bool:
    if string.casefold() in ["true", "1", "yes", "y"]:
        return True
    if string.casefold() in ["false", "0", "no", "n"]:
        return False
    msg = f"Could not parse {string=} as bool."
    raise ValueError(msg)


def _format_error(*, code: DatasetError, message: str) -> dict[str, str]:
    """Formatter for JSON bodies of OpenML error codes."""
    return {"code": str(code), "message": message}


def _format_parquet_url(dataset: Row) -> str | None:
    if dataset.format.lower() != DatasetFileFormat.ARFF:
        return None

    minio_base_url = load_configuration()["minio_base_url"]
    prefix = dataset.did // 10_000
    return f"{minio_base_url}/datasets/{prefix:04d}/{dataset.did:04d}/dataset_{dataset.did}.pq"


def _format_dataset_url(dataset: Row) -> str:
    base_url = load_configuration()["arff_base_url"]
    filename = f"{html.escape(dataset.name)}.{dataset.format.lower()}"
    return f"{base_url}/data/v1/download/{dataset.file_id}/{filename}"


def _safe_unquote(text: str | None) -> str | None:
    """Remove any open and closing quotes and return the remainder if non-empty."""
    if not text:
        return None
    return text.strip("'\"") or None


def _csv_as_list(text: str | None, *, unquote_items: bool = True) -> list[str]:
    """Return comma-separated values in `text` as list, optionally remove quotes."""
    if not text:
        return []
    chars_to_strip = "'\"\t " if unquote_items else "\t "
    return [item.strip(chars_to_strip) for item in text.split(",")]
