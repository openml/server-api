from datetime import datetime
from enum import StrEnum

from fastapi import APIRouter
from pydantic import BaseModel, Field, HttpUrl

router = APIRouter(prefix="/datasets", tags=["datasets"])


class DatasetFileFormat(StrEnum):
    ARFF = "ARFF"
    PARQUET = "parquet"


class DatasetLicence(StrEnum):
    CC0 = "Public"
    OTHER = "other"


class Visibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class DatasetStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    IN_PROCESSING = "in processing"


class DatasetMetadata(BaseModel):
    id_: int = Field(example=1)
    name: str = Field(example="Anneal")
    version: int = Field(example=2)
    description: str = Field(example="The original Annealing dataset from UCI.")
    format_: DatasetFileFormat = Field(example=DatasetFileFormat.ARFF)
    upload_date: datetime = Field(example=datetime(2014, 4, 6, 23, 19, 20))
    licence: DatasetLicence = Field(example=DatasetLicence.CC0)
    url: HttpUrl = Field(
        example="https://www.openml.org/data/download/1/dataset_1_anneal.arff",
        description="URL of the dataset data file.",
    )
    file_id: int = Field(example=1)
    default_target_attribute: str = Field(example="class")
    version_label: str = Field(
        example="2",
        description="Not sure how this relates to `version`.",
    )
    tag: list[str] = Field(example=["study_1", "uci"])
    visibility: Visibility = Field(example=Visibility.PUBLIC)
    original_data_url: HttpUrl = Field(example="https://www.openml.org/d/2")
    status: DatasetStatus = Field(example=DatasetStatus.ACTIVE)
    md5_checksum: str = Field(example="d01f6ccd68c88b749b20bbe897de3713")


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_dataset(_dataset_id: int) -> DatasetMetadata:
    return DatasetMetadata()  # type: ignore[call-arg]


@router.get(
    path="/data/{dataset_id}",
    description="Get old-style wrapped meta-data for dataset with ID `dataset_id`.",
)
def get_dataset_wrapped(_dataset_id: int) -> dict[str, DatasetMetadata]:
    return {"data_set_description": DatasetMetadata()}  # type: ignore[call-arg]
