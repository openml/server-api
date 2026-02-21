from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.datasets.openml import Visibility


class DatasetUploadMetadata(BaseModel):
    """Metadata provided alongside the uploaded Parquet file."""

    name: str = Field(description="Human-readable name of the dataset.", min_length=1, max_length=256)
    description: str = Field(description="Description of the dataset.", min_length=1)
    default_target_attribute: str = Field(
        default="",
        description="Comma-separated column name(s) to use as the prediction target.",
    )
    visibility: Visibility = Field(default=Visibility.PUBLIC, description="Dataset visibility.")
    licence: str = Field(default="CC0", description="Dataset licence.")
    language: str = Field(default="English", description="Language of the dataset.")
    citation: str = Field(default="", description="Citation string for the dataset.")
    original_data_url: str = Field(default="", description="URL of the original data source.")
    paper_url: str = Field(default="", description="URL of a related paper.")
    collection_date: str = Field(default="", description="When the data was collected.")


class DatasetUploadResponse(BaseModel):
    """Response returned after a successful dataset upload."""

    upload_dataset: dict[str, int]
