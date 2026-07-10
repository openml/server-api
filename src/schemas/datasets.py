"""Defines schemas for API responses relating to Datasets."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl

from core.types import Identifier


class DatasetFileFormat(StrEnum):
    """Allowed file formats for data files."""

    ARFF = "arff"
    SPARSE_ARFF = "sparse_arff"
    PARQUET = "parquet"


class Visibility(StrEnum):
    """Possible visibility statuses."""

    PUBLIC = "public"
    PRIVATE = "private"


class DatasetStatus(StrEnum):
    """Possible dataset statuses.

    - In Preparation: any uploaded dataset isn't yet successfully processed.
    - Active: any uploaded dataset that has successfully been processed.
    - Deactivated: use of the dataset is discouraged.
    """

    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    IN_PREPARATION = "in_preparation"


class Quality(BaseModel):
    """A computed quality (meta-feature) of the dataset."""

    name: str
    value: float | None


class FeatureType(StrEnum):
    """The type of a feature (column) in the dataset."""

    NUMERIC = "numeric"
    NOMINAL = "nominal"
    STRING = "string"


class Feature(BaseModel):
    """Metadata about a feature (column) in the dataset."""

    index: int
    name: str
    data_type: FeatureType
    ontology: list[str] | None = None
    is_target: bool
    is_ignore: bool
    is_row_identifier: bool
    number_of_missing_values: int
    nominal_values: list[str] | None


class DatasetMetadata(BaseModel):
    """Metadata for a dataset."""

    id: Identifier = Field(json_schema_extra={"example": 1})
    visibility: Visibility = Field(json_schema_extra={"example": Visibility.PUBLIC})
    status: DatasetStatus = Field(json_schema_extra={"example": DatasetStatus.ACTIVE})

    name: str = Field(json_schema_extra={"example": "Anneal"})
    licence: str = Field(json_schema_extra={"example": "CC0"})
    version: int = Field(json_schema_extra={"example": 2})
    version_label: str = Field(
        json_schema_extra={
            "example": 2,
            "description": "Not sure how this relates to `version`.",
        },
    )
    language: str = Field(json_schema_extra={"example": "English"})

    creators: list[str] = Field(
        json_schema_extra={"example": ["David Sterling", "Wray Buntine"]},
        alias="creator",
    )
    contributors: list[str] = Field(
        json_schema_extra={"example": ["David Sterling", "Wray Buntine"]},
        alias="contributor",
    )
    citation: str = Field(
        json_schema_extra={"example": "https://archive.ics.uci.edu/ml/citation_policy.html"},
    )
    paper_url: HttpUrl | None = Field(
        json_schema_extra={
            "example": "http://digital.library.adelaide.edu.au/dspace/handle/2440/15227",
        },
    )
    upload_date: datetime = Field(
        json_schema_extra={"example": str(datetime(2014, 4, 6, 23, 12, 20, tzinfo=UTC))},
    )
    processing_date: datetime | None = Field(
        json_schema_extra={"example": str(datetime(2019, 7, 9, 15, 22, 3, tzinfo=UTC))},
    )
    processing_error: str | None = Field(
        json_schema_extra={"example": "Please provide description XML."},
        alias="error",
    )
    processing_warning: str | None = Field(alias="warning")
    collection_date: str | None = Field(json_schema_extra={"example": "1990"})

    description: str = Field(
        json_schema_extra={"example": "The original Annealing dataset from UCI."},
    )
    description_version: Identifier = Field(json_schema_extra={"example": 2})
    tags: list[str] = Field(json_schema_extra={"example": ["study_1", "uci"]}, alias="tag")
    default_target_attribute: list[str] = Field(json_schema_extra={"example": "class"})
    ignore_attribute: list[str] = Field(json_schema_extra={"example": "sensitive_feature"})
    row_id_attribute: list[str] = Field(json_schema_extra={"example": "ssn"})

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
    file_id: Identifier = Field(json_schema_extra={"example": 1})
    format: DatasetFileFormat = Field(
        json_schema_extra={"example": DatasetFileFormat.ARFF},
    )
    original_data_url: list[HttpUrl] | None = Field(
        json_schema_extra={"example": "https://www.openml.org/d/2"},
    )
    md5_checksum: str = Field(json_schema_extra={"example": "d01f6ccd68c88b749b20bbe897de3713"})
