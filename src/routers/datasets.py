import html
import http.client
from enum import IntEnum
from typing import Any, cast

from database.datasets import get_dataset as db_get_dataset
from database.datasets import (
    get_file,
    get_latest_dataset_description,
    get_latest_processing_update,
    get_latest_status_update,
    get_tags,
)
from fastapi import APIRouter, HTTPException
from schemas.datasets.openml import DatasetMetadata, DatasetStatus, Visibility

router = APIRouter(prefix="/datasets", tags=["datasets"])
# We add separate endpoints for old-style JSON responses,
# so they don't clutter the schema of the new API, and are easily removed later.
router_old_format = APIRouter(prefix="/old/datasets", tags=["datasets"])


class DatasetError(IntEnum):
    NOT_FOUND = 111
    NO_ACCESS = 112
    NO_DATA_FILE = 113


def format_error(*, code: DatasetError, message: str) -> dict[str, int | str]:
    """Formatter for JSON bodies of OpenML error codes."""
    return {"code": code, "message": message}


def user_has_access(dataset: dict[str, Any], _user: Any) -> bool:
    """Determine if `user` has the right to view `dataset`."""
    # TODO: when private, check if user is uploader or admin
    return cast(str, dataset["visibility"]) == Visibility.PUBLIC


def format_parquet_url(dataset: dict[str, Any]) -> str | None:
    if dataset["format"] == "Sparse_ARFF":
        return None

    minio_base_url = "https://openml1.win.tue.nl"
    return f"{minio_base_url}/dataset{dataset['did']}/dataset_{dataset['did']}.pq"


def format_dataset_url(dataset: dict[str, Any]) -> str:
    base_url = "https://test.openml.org"
    filename = f"{html.escape(dataset['name'])}.{dataset['format'].lower()}"
    return f"{base_url}/data/v1/download/{dataset['file_id']}/{filename}"


def safe_unquote(text: str | None) -> str | None:
    """Remove any open and closing quotes and return the remainder if non-empty."""
    if not text:
        return None
    return text.strip("'\"") or None


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_dataset(dataset_id: int) -> DatasetMetadata:
    if not (dataset := db_get_dataset(dataset_id)):
        error = format_error(code=DatasetError.NOT_FOUND, message="Unknown dataset")
        raise HTTPException(status_code=http.client.PRECONDITION_FAILED, detail=error)

    user = None  # get_user(...)
    if not user_has_access(dataset, user):
        error = format_error(code=DatasetError.NO_ACCESS, message="No access granted")
        raise HTTPException(status_code=http.client.PRECONDITION_FAILED, detail=error)

    if not (dataset_file := get_file(dataset["file_id"])):
        error = format_error(
            code=DatasetError.NO_DATA_FILE,
            message="No data file found",
        )
        raise HTTPException(status_code=http.client.PRECONDITION_FAILED, detail=error)

    tags = get_tags(dataset_id)
    description = get_latest_dataset_description(dataset_id)
    date_processed = get_date_processed(dataset_id)
    status = get_latest_status_update(dataset_id)

    status_ = DatasetStatus(status["status"]) if status else DatasetStatus.IN_PROCESSING

    description_ = ""
    if description:
        description_ = description["description"].replace("\r", "").strip()

    dataset_url = format_dataset_url(dataset)
    parquet_url = format_parquet_url(dataset)

    contributors = (
        [contributor.strip("\"'") for contributor in dataset["contributor"].split(", ")]
        if dataset["contributor"]
        else []
    )

    creators = (
        [creator.strip("'\"") for creator in dataset["creator"].split(", ")]
        if dataset["creator"]
        else []
    )

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
        processing_date=date_processed,
        description=description_,
        description_version=description["version"] if description else 0,
        tag=tags,
        default_target_attribute=safe_unquote(dataset["default_target_attribute"]),
        ignore_attribute=safe_unquote(dataset["ignore_attribute"]),
        row_id_attribute=safe_unquote(dataset["row_id_attribute"]),
        url=dataset_url,
        parquet_url=parquet_url,
        minio_url=parquet_url,
        file_id=dataset["file_id"],
        format=dataset["format"],
        paper_url=dataset["paper_url"] or None,
        original_data_url=dataset["original_data_url"] or None,
        collection_date=dataset["collection_date"],
        md5_checksum=dataset_file["md5_hash"],
    )


def get_date_processed(dataset_id: int) -> str | None:
    if not (data_processed := get_latest_processing_update(dataset_id)):
        return None

    date_processed = data_processed["processing_date"]
    warning = data_processed["warning"]
    error = data_processed["error"]
    if warning or error:
        msg = f"Dataset processed with {warning=} and {error=}. Behavior unclear."
        raise NotImplementedError(msg)
    return cast(str, date_processed)


@router_old_format.get(
    path="/{dataset_id}",
    description="Get old-style wrapped meta-data for dataset with ID `dataset_id`.",
)
def get_dataset_wrapped(dataset_id: int) -> dict[str, dict[str, Any]]:
    dataset = get_dataset(dataset_id).dict(by_alias=True)
    if dataset.get("processing_date"):
        dataset["processing_date"] = str(dataset["processing_date"]).replace("T", " ")
    if dataset.get("parquet_url"):
        dataset["parquet_url"] = dataset["parquet_url"].replace("https", "http")

    manual = []
    # ref test.openml.org/d/33 (contributor) and d/34 (creator)
    #   contributor/creator in database is '""'
    #   json content is []
    for field in ["contributor", "creator"]:
        if dataset[field] == [""]:
            dataset[field] = []
            manual.append(field)

    for field, value in list(dataset.items()):
        if field in manual:
            continue
        if isinstance(value, int):
            dataset[field] = str(value)
        elif isinstance(value, list) and len(value) == 1:
            dataset[field] = str(value[0])
        if not dataset[field]:
            del dataset[field]

    return {"data_set_description": dataset}
