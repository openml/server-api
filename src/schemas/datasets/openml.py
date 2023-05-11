from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class DatasetSchema(StrEnum):
    DCAT_AP = "dcat-ap"
    OPENML = "openml"


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
    id_: int = Field(example=1, alias="id")
    name: str = Field(example="Anneal")
    version: int = Field(example=2)
    description: str = Field(example="The original Annealing dataset from UCI.")
    format_: DatasetFileFormat = Field(example=DatasetFileFormat.ARFF, alias="format")
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
