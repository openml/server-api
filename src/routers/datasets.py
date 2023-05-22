from typing import cast

from fastapi import APIRouter

# from database.datasets import get_dataset_description
from schemas.datasets import DatasetSchema
from schemas.datasets.convertor import openml_dataset_to_dcat
from schemas.datasets.dcat import DcatApWrapper
from schemas.datasets.mldcat_ap import JsonLDGraph, convert_to_mldcat_ap
from schemas.datasets.openml import DatasetMetadata

router = APIRouter(prefix="/datasets", tags=["datasets"])
# We add separate endpoints for old-style JSON responses,
# so they don't clutter the schema of the new API, and are easily removed later.
router_old_format = APIRouter(prefix="/old/datasets", tags=["datasets"])


DATASET_EXAMPLE = {
    "id": 1,
    "name": "Anneal",
    "version": 2,
    "description": "The original Annealing dataset from UCI.",
    "format": "ARFF",
    "upload_date": "2014-04-06T23:19:20",
    "licence": "Public",
    "url": "https://www.openml.org/data/download/1/dataset_1_anneal.arff",
    "file_id": 1,
    "default_target_attribute": "class",
    "version_label": "2",
    "tag": [
        "study_1",
        "uci",
    ],
    "visibility": "public",
    "original_data_url": "https://www.openml.org/d/2",
    "status": "active",
    "md5_checksum": "d01f6ccd68c88b749b20bbe897de3713",
}


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_dataset(
    _dataset_id: int,
    schema: DatasetSchema,
) -> DatasetMetadata | DcatApWrapper | JsonLDGraph:
    # if _dataset_id > 0:
    #     example = get_dataset_description(_dataset_id)
    # else:
    example = DatasetMetadata.parse_obj(DATASET_EXAMPLE)

    if schema == DatasetSchema.MLDCAT_AP:
        return convert_to_mldcat_ap(example)
    if schema == DatasetSchema.DCAT_AP:
        return openml_dataset_to_dcat(example)
    return example


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
