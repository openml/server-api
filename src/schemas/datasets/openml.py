from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class DatasetFileFormat(StrEnum):
    ARFF = "arff"
    SPARSE_ARFF = "sparse_arff"
    PARQUET = "parquet"


class Visibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class DatasetStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    IN_PROCESSING = "in processing"
    IN_PREPARATION = "in_preparation"


class Quality(BaseModel):
    name: str
    value: float | None


class FeatureType(StrEnum):
    NUMERIC = "numeric"
    NOMINAL = "nominal"
    STRING = "string"


class Feature(BaseModel):
    index: int
    name: str
    data_type: FeatureType
    is_target: bool
    is_ignore: bool
    is_row_identifier: bool
    number_of_missing_values: int
    nominal_values: list[str] | None


class EstimationProcedure(BaseModel):
    id_: int = Field(serialization_alias="id")
    task_type_id: int
    name: str
    type_: str = Field(serialization_alias="type")
    percentage: int | None
    repeats: int | None
    folds: int | None
    stratified_sampling: bool | None


class DatasetMetadata(BaseModel):
    name: str = Field(json_schema_extra={"example": "Anneal"})
    licence: str = Field(json_schema_extra={"example": "CC0"})
    version: int = Field(json_schema_extra={"example": 2})
    version_label: str | None = Field(
        json_schema_extra={
            "example": 2,
            "description": "Not sure how this relates to `version`.",
        },
        max_length=128,
    )
    language: str | None = Field(
        json_schema_extra={"example": "English"},
        max_length=128,
    )

    creators: list[str] = Field(
        json_schema_extra={"example": ["David Sterling", "Wray Buntine"]},
        alias="creator",
    )
    contributors: list[str] = Field(
        json_schema_extra={"example": ["David Sterling", "Wray Buntine"]},
        alias="contributor",
    )
    citation: str | None = Field(
        json_schema_extra={"example": "https://archive.ics.uci.edu/ml/citation_policy.html"},
    )
    paper_url: HttpUrl | None = Field(
        json_schema_extra={
            "example": "http://digital.library.adelaide.edu.au/dspace/handle/2440/15227",
        },
    )
    collection_date: str | None = Field(json_schema_extra={"example": "1990"})

    description: str = Field(
        json_schema_extra={"example": "The original Annealing dataset from UCI."},
    )
    default_target_attribute: list[str] = Field(json_schema_extra={"example": "class"})
    ignore_attribute: list[str] = Field(json_schema_extra={"example": "sensitive_feature"})
    row_id_attribute: list[str] = Field(json_schema_extra={"example": "ssn"})

    format_: DatasetFileFormat = Field(
        json_schema_extra={"example": DatasetFileFormat.ARFF},
        alias="format",
    )
    original_data_url: list[HttpUrl] | None = Field(
        json_schema_extra={"example": "https://www.openml.org/d/2"},
    )


class DatasetMetadataView(DatasetMetadata):
    id_: int = Field(json_schema_extra={"example": 1}, alias="id")
    visibility: Visibility = Field(json_schema_extra={"example": Visibility.PUBLIC})
    status: DatasetStatus = Field(json_schema_extra={"example": DatasetStatus.ACTIVE})
    description_version: int = Field(json_schema_extra={"example": 2})
    tags: list[str] = Field(json_schema_extra={"example": ["study_1", "uci"]}, alias="tag")
    upload_date: datetime = Field(
        json_schema_extra={"example": str(datetime(2014, 4, 6, 23, 12, 20))},
    )
    processing_date: datetime | None = Field(
        json_schema_extra={"example": str(datetime(2019, 7, 9, 15, 22, 3))},
    )
    processing_error: str | None = Field(
        json_schema_extra={"example": "Please provide description XML."},
        alias="error",
    )
    processing_warning: str | None = Field(alias="warning")
    file_id: int = Field(json_schema_extra={"example": 1})
    url: HttpUrl = Field(
        json_schema_extra={
            "example": "https://www.openml.org/data/download/1/dataset_1_anneal.arff",
            "description": "URL of the main dataset data file.",
        },
    )
    parquet_url: HttpUrl | None = Field(
        json_schema_extra={
            "example": "http://openml1.win.tue.nl/dataset2/dataset_2.pq",
            "description": "URL of the parquet dataset data file.",
        },
    )
    md5_checksum: str = Field(json_schema_extra={"example": "d01f6ccd68c88b749b20bbe897de3713"})


class Task(BaseModel):
    id_: int = Field(serialization_alias="id", json_schema_extra={"example": 59})
    name: str = Field(
        json_schema_extra={"example": "Task 59:  mfeat-pixel (Supervised Classification)"},
    )
    task_type_id: int = Field(json_schema_extra={"example": 1})
    task_type: str = Field(json_schema_extra={"example": "Supervised Classification"})
    input_: list[dict[str, Any]] = Field(serialization_alias="input")
    output: list[dict[str, Any]]
    tags: list[str] = Field(default_factory=list)
