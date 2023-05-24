import http.client
from typing import Any, cast

from database.datasets import get_dataset as db_get_dataset
from database.datasets import get_dataset_description, get_file, get_tags
from fastapi import APIRouter, HTTPException
from schemas.datasets import DatasetSchema
from schemas.datasets.convertor import openml_dataset_to_dcat
from schemas.datasets.dcat import DcatApWrapper
from schemas.datasets.mldcat_ap import JsonLDGraph, convert_to_mldcat_ap
from schemas.datasets.openml import DatasetMetadata, Visibility

router = APIRouter(prefix="/datasets", tags=["datasets"])
# We add separate endpoints for old-style JSON responses,
# so they don't clutter the schema of the new API, and are easily removed later.
router_old_format = APIRouter(prefix="/old/datasets", tags=["datasets"])


def format_error(*, code: int, message: str) -> dict[str, int | str]:
    """Formatter for JSON bodies of OpenML error codes."""
    return {"code": code, "message": message}


def user_has_access(dataset: dict[str, Any], _user: Any) -> bool:
    """Determine if `user` has the right to view `dataset`."""
    return cast(str, dataset["visibility"]) == Visibility.PUBLIC


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_dataset(
    dataset_id: int,
    schema: DatasetSchema,
) -> DatasetMetadata | DcatApWrapper | JsonLDGraph:
    if not (dataset := db_get_dataset(dataset_id)):
        raise HTTPException(
            status_code=http.client.PRECONDITION_FAILED,
            detail=format_error(code=111, message="Unknown dataset"),
        )

    user = None  # get_user(...)
    if not user_has_access(dataset, user):
        raise HTTPException(
            status_code=http.client.PRECONDITION_FAILED,
            detail=format_error(code=112, message="No access granted"),
        )

    if not (dataset_file := get_file(dataset["file_id"])):
        raise HTTPException(
            status_code=http.client.PRECONDITION_FAILED,
            detail=format_error(code=113, message="Could not find data file record"),
        )

    tags = get_tags(dataset_id)

    description = get_dataset_description(dataset, dataset_file, tags)
    if schema == DatasetSchema.MLDCAT_AP:
        return convert_to_mldcat_ap(description)
    if schema == DatasetSchema.DCAT_AP:
        return openml_dataset_to_dcat(description)
    return description


@router_old_format.get(
    path="/{dataset_id}",
    description="Get old-style wrapped meta-data for dataset with ID `dataset_id`.",
)
def get_dataset_wrapped(dataset_id: int) -> dict[str, DatasetMetadata]:
    dataset = get_dataset(dataset_id, schema=DatasetSchema.OPENML)
    # TODO: convert tags from list to str)
    # TODO: convert contributor from list to str
    # TODO: Check all types are consistent
    return {"data_set_description": cast(DatasetMetadata, dataset)}
