import html
import http.client
from collections import namedtuple
from enum import IntEnum
from typing import Annotated, Any

from database.datasets import get_dataset as db_get_dataset
from database.datasets import (
    get_file,
    get_latest_dataset_description,
    get_latest_processing_update,
    get_latest_status_update,
    get_tags,
)
from database.setup import expdb_database, user_database
from database.users import APIKey, get_user_groups_for, get_user_id_for
from fastapi import APIRouter, Depends, HTTPException
from schemas.datasets.openml import (
    DatasetFileFormat,
    DatasetMetadata,
    DatasetStatus,
    Visibility,
)
from sqlalchemy import Engine

router = APIRouter(prefix="/datasets", tags=["datasets"])


class DatasetError(IntEnum):
    NOT_FOUND = 111
    NO_ACCESS = 112
    NO_DATA_FILE = 113


processing_info = namedtuple("processing_info", ["date", "warning", "error"])


def _get_processing_information(dataset_id: int, engine: Engine) -> processing_info:
    """Return processing information, if any. Otherwise, all fields `None`."""
    if not (data_processed := get_latest_processing_update(dataset_id, engine)):
        return processing_info(date=None, warning=None, error=None)

    date_processed = data_processed["processing_date"]
    warning = data_processed["warning"].strip() if data_processed["warning"] else None
    error = data_processed["error"].strip() if data_processed["error"] else None
    return processing_info(date=date_processed, warning=warning, error=error)


def _format_error(*, code: DatasetError, message: str) -> dict[str, str]:
    """Formatter for JSON bodies of OpenML error codes."""
    return {"code": str(code), "message": message}


def _user_has_access(
    dataset: dict[str, Any],
    engine: Engine,
    api_key: APIKey | None = None,
) -> bool:
    """Determine if user of `api_key` has the right to view `dataset`."""
    if dataset["visibility"] == Visibility.PUBLIC:
        return True
    if not api_key:
        return False

    if not (user_id := get_user_id_for(api_key=api_key, engine=engine)):
        return False

    if user_id == dataset["uploader"]:
        return True

    user_groups = get_user_groups_for(user_id=user_id, engine=engine)
    ADMIN_GROUP = 1
    return ADMIN_GROUP in user_groups


def _format_parquet_url(dataset: dict[str, Any]) -> str | None:
    if dataset["format"].lower() != DatasetFileFormat.ARFF:
        return None

    minio_base_url = "https://openml1.win.tue.nl"
    return f"{minio_base_url}/dataset{dataset['did']}/dataset_{dataset['did']}.pq"


def _format_dataset_url(dataset: dict[str, Any]) -> str:
    base_url = "https://test.openml.org"
    filename = f"{html.escape(dataset['name'])}.{dataset['format'].lower()}"
    return f"{base_url}/data/v1/download/{dataset['file_id']}/{filename}"


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


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_dataset(
    dataset_id: int,
    api_key: APIKey | None = None,
    user_db: Annotated[Engine, Depends(user_database)] = None,
    expdb_db: Annotated[Engine, Depends(expdb_database)] = None,
) -> DatasetMetadata:
    if not (dataset := db_get_dataset(dataset_id, expdb_db)):
        error = _format_error(code=DatasetError.NOT_FOUND, message="Unknown dataset")
        raise HTTPException(status_code=http.client.NOT_FOUND, detail=error)

    if not _user_has_access(dataset=dataset, api_key=api_key, engine=user_db):
        error = _format_error(code=DatasetError.NO_ACCESS, message="No access granted")
        raise HTTPException(status_code=http.client.FORBIDDEN, detail=error)

    if not (dataset_file := get_file(dataset["file_id"], user_db)):
        error = _format_error(
            code=DatasetError.NO_DATA_FILE,
            message="No data file found",
        )
        raise HTTPException(status_code=http.client.PRECONDITION_FAILED, detail=error)

    tags = get_tags(dataset_id, expdb_db)
    description = get_latest_dataset_description(dataset_id, expdb_db)
    processing_result = _get_processing_information(dataset_id, expdb_db)
    status = get_latest_status_update(dataset_id, expdb_db)

    status_ = DatasetStatus(status["status"]) if status else DatasetStatus.IN_PREPARATION

    description_ = ""
    if description:
        description_ = description["description"].replace("\r", "").strip()

    dataset_url = _format_dataset_url(dataset)
    parquet_url = _format_parquet_url(dataset)

    contributors = _csv_as_list(dataset["contributor"], unquote_items=True)
    creators = _csv_as_list(dataset["creator"], unquote_items=True)
    ignore_attribute = _csv_as_list(dataset["ignore_attribute"], unquote_items=True)
    row_id_attribute = _csv_as_list(dataset["row_id_attribute"], unquote_items=True)
    original_data_url = _csv_as_list(dataset["original_data_url"], unquote_items=True)

    # Not sure which properties are set by this bit:
    # foreach( $this->xml_fields_dataset['csv'] as $field ) {
    #   $dataset->{$field} = getcsv( $dataset->{$field} );
    # }

    return DatasetMetadata(
        id=dataset["did"],
        visibility=dataset["visibility"],
        status=status_,
        name=dataset["name"],
        licence=dataset["licence"],
        version=dataset["version"],
        version_label=dataset["version_label"] or "",
        language=dataset["language"] or "",
        creator=creators,
        contributor=contributors,
        citation=dataset["citation"] or "",
        upload_date=dataset["upload_date"],
        processing_date=processing_result.date,
        warning=processing_result.warning,
        error=processing_result.error,
        description=description_,
        description_version=description["version"] if description else 0,
        tag=tags,
        default_target_attribute=_safe_unquote(dataset["default_target_attribute"]),
        ignore_attribute=ignore_attribute,
        row_id_attribute=row_id_attribute,
        url=dataset_url,
        parquet_url=parquet_url,
        minio_url=parquet_url,
        file_id=dataset["file_id"],
        format=dataset["format"].lower(),
        paper_url=dataset["paper_url"] or None,
        original_data_url=original_data_url,
        collection_date=dataset["collection_date"],
        md5_checksum=dataset_file["md5_hash"],
    )
