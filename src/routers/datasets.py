from fastapi import APIRouter
from schemas.datasets.convertor import openml_dataset_to_dcat
from schemas.datasets.dcat import DcatApWrapper
from schemas.datasets.openml import DatasetMetadata

router = APIRouter(prefix="/datasets", tags=["datasets"])
# We add separate endpoints for old-style JSON responses,
# so they don't clutter the schema of the new API, and are easily removed later.
router_old_format = APIRouter(prefix="/old/datasets", tags=["datasets"])


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_dataset(_dataset_id: int) -> DatasetMetadata | DcatApWrapper:
    example = DatasetMetadata.parse_obj(
        {
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
        },
    )
    return openml_dataset_to_dcat(example)


@router_old_format.get(
    path="/{dataset_id}",
    description="Get old-style wrapped meta-data for dataset with ID `dataset_id`.",
)
def get_dataset_wrapped(_dataset_id: int) -> dict[str, DatasetMetadata]:
    return {"data_set_description": DatasetMetadata()}  # type: ignore[call-arg]