"""Pydantic schemas for the setup API endpoints."""

from pydantic import BaseModel, ConfigDict


class SetupParameter(BaseModel):
    """Schema representing an individual parameter within a setup."""

    id: int
    flow_id: int
    flow_name: str
    full_name: str
    parameter_name: str
    name: str
    data_type: str | None = None
    default_value: str | None = None
    value: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SetupParameters(BaseModel):
    """Schema representing the grouped properties of a setup and its parameters."""

    setup_id: int
    flow_id: int
    parameter: list[SetupParameter] | None = None

    model_config = ConfigDict(from_attributes=True)


class SetupResponse(BaseModel):
    """Schema for the complete response of the GET /setup/{id} endpoint."""

    setup_parameters: SetupParameters

    model_config = ConfigDict(from_attributes=True)
