"""
Based on MLDCAT-AP 1.0.0: https://semiceu.github.io/MLDCAT-AP/releases/1.0.0/

This is an application profile, aimed to extend the use of DCAT-AP,
originally envisaged for the description of a machine learning process,
developed in collaboration with OpenML.
"""

from __future__ import annotations

from abc import ABC
from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field, HttpUrl, field_serializer, model_serializer

from schemas.datasets.openml import DatasetStatus, Visibility


class JsonLDQualifiedLiteral(BaseModel):
    """Base class for all JSON-LD objects"""

    type_: str = Field(serialization_alias="@type")
    value: str = Field(serialization_alias="@value")

    model_config = {"populate_by_name": True, "extra": "forbid"}


JsonLiteral = JsonLDQualifiedLiteral | str


class JsonLDObject(BaseModel, ABC):
    """Base class for all JSON-LD objects"""

    id_: str = Field(serialization_alias="@id")
    type_: str = Field(serialization_alias="@type")

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


T = TypeVar("T", bound=JsonLDObject)


class JsonLDObjectReference(BaseModel, Generic[T]):
    id_: str = Field(serialization_alias="@id")

    model_config = {"populate_by_name": True, "extra": "forbid"}

    @classmethod
    def to(cls, json_ld_object: T) -> JsonLDObjectReference[T]:
        """Create a reference to `json_ld_object`"""
        return cls(id_=json_ld_object.id_)

    @model_serializer
    def ser_model(self) -> str:
        return self.id_


class AccessRights(StrEnum):
    """Recommend values for 'access rights' within DCAT-AP context"""

    #  https://op.europa.eu/en/web/eu-vocabularies/dataset/-/resource?uri=http://publications.europa.eu/resource/dataset/access-right
    PUBLIC = "PUBLIC"
    RESTRICTED = "RESTRICTED"
    NON_PUBLIC = "NON_PUBLIC"


class Agent(JsonLDObject):
    """Any entity carrying out actions with respect to the (Core) entities Catalogue,
    Datasets, Data Services and Distributions. If the Agent is an organisation,
    the use of the Organization Ontology is recommended.
    """

    type_: Literal["Agent"] = Field(default="Agent", serialization_alias="@type")
    name: list[JsonLiteral] = Field(
        default_factory=list,
        min_length=1,
        serialization_alias="Agent.name",
    )


class MD5Checksum(JsonLDObject):
    """A value that allows the contents of a file to be authenticated.
    This class allows the results of a variety of checksum and cryptographic
    message digest algorithms to be represented.
    """

    type_: Literal["Checksum"] = Field(default="Checksum", serialization_alias="@type")
    algorithm: Literal["http://spdx.org/rdf/terms#checksumAlgorithm_md5"] = Field(
        "http://spdx.org/rdf/terms#checksumAlgorithm_md5",
        serialization_alias="Checksum.algorithm",
    )
    value: str = Field(serialization_alias="Checksum.checksumValue")


class FeatureType(StrEnum):
    NOMINAL = "Nominal"
    NUMERIC = "Numeric"


class Feature(JsonLDObject):
    type_: Literal["Feature"] = Field(default="Feature", serialization_alias="@type")
    name: str = Field(serialization_alias="Feature.name")
    feature_type: str = Field(serialization_alias="Feature.type")


class Quality(JsonLDObject):
    type_: Literal["Quality"] = Field(default="Quality", serialization_alias="@type")
    quality_type: str = Field(serialization_alias="Quality.type")
    value: JsonLiteral = Field(serialization_alias="Quality.value")


class Distribution(JsonLDObject):
    type_: Literal["Distribution"] = Field(default="Distribution", serialization_alias="@type")
    # required
    access_url: list[HttpUrl] = Field(
        default_factory=list,
        min_length=1,
        serialization_alias="Distribution.accessUrl",
    )
    has_feature: list[JsonLDObjectReference[Feature]] = Field(
        default_factory=list,
        serialization_alias="Distribution.hasFeature",
        min_length=1,
    )
    has_quality: list[JsonLDObjectReference[Quality]] = Field(
        default_factory=list,
        serialization_alias="Distribution.hasQuality",
        min_length=1,
    )

    # other
    byte_size: JsonLiteral | None = Field(serialization_alias="Distribution.byteSize", default=None)
    default_target_attribute: JsonLiteral | None = Field(
        serialization_alias="Distribution.defaultTargetAttribute",
        default=None,
    )
    download_url: list[HttpUrl] = Field(
        default_factory=list,
        serialization_alias="Distribution.downloadUrl",
    )
    format_: JsonLiteral | None = Field(serialization_alias="Distribution.format", default=None)
    identifier: JsonLiteral | None = Field(
        default=None,
        serialization_alias="Distribution.identifier",
    )
    ignore_attribute: list[JsonLiteral] = Field(
        default_factory=list,
        serialization_alias="Distribution.ignoreAttribute",
    )
    processing_error: JsonLiteral | None = Field(
        serialization_alias="Distribution.processingError",
        default=None,
    )
    processing_warning: JsonLiteral | None = Field(
        serialization_alias="Distribution.processingWarning",
        default=None,
    )
    processing_data: JsonLiteral | None = Field(
        serialization_alias="Distribution.processingDate",
        default=None,
    )
    row_id_attribute: JsonLiteral | None = Field(
        serialization_alias="Distribution.rowIDAttribute",
        default=None,
    )
    title: list[JsonLiteral] = Field(default_factory=list, serialization_alias="Distribution.title")
    checksum: JsonLDObjectReference[MD5Checksum] | None = Field(
        default=None,
        serialization_alias="Distribution.checksum",
    )

    access_service: list[JsonLDObjectReference[DataService]] = Field(
        default_factory=list,
        serialization_alias="Distribution.accessService",
    )


class Dataset(JsonLDObject):
    type_: Literal["Dataset"] = Field(default="Dataset", serialization_alias="@type")
    # required
    collection_date: JsonLiteral = Field(serialization_alias="Dataset.collectionDate")
    description: list[JsonLiteral] = Field(
        default_factory=list,
        min_length=1,
        serialization_alias="Dataset.description",
    )
    title: list[JsonLiteral] = Field(
        default_factory=list,
        min_length=1,
        serialization_alias="Dataset.title",
    )

    # other
    access_rights: AccessRights | None = Field(
        serialization_alias="Dataset.accessRights",
        default=None,
    )
    contributor: list[JsonLDObjectReference[Agent]] = Field(
        default_factory=list,
        serialization_alias="Dataset.contributor",
    )
    creator: Agent | None = Field(default=None, serialization_alias="Dataset.creator")
    distribution: list[JsonLDObjectReference[Distribution]] = Field(
        default_factory=list,
        serialization_alias="Dataset.distribution",
    )
    has_version: list[JsonLDObjectReference[Dataset]] = Field(
        default_factory=list,
        serialization_alias="Dataset.hasVersion",
    )
    identifier: list[JsonLiteral] = Field(
        default_factory=list,
        serialization_alias="Dataset.identifier",
    )
    is_referenced_by: list[JsonLiteral] = Field(
        default_factory=list,
        serialization_alias="Dataset.isReferencedBy",
    )
    is_version_of: list[JsonLDObjectReference[Dataset]] = Field(
        default_factory=list,
        serialization_alias="Dataset.isVersionOf",
    )
    issued: JsonLiteral | None = Field(default=None, serialization_alias="Dataset.issued")
    keyword: list[JsonLiteral] = Field(default_factory=list, serialization_alias="Dataset.keyword")
    landing_page: list[JsonLiteral] = Field(
        default_factory=list,
        serialization_alias="Dataset.landingPage",
    )
    publisher: JsonLDObjectReference[Agent] | None = Field(
        default=None,
        serialization_alias="Dataset.publisher",
    )
    status: DatasetStatus | None = Field(default=None, serialization_alias="Dataset.status")
    version_info: JsonLiteral | None = Field(
        serialization_alias="Dataset.versionInfo",
        default=None,
    )
    version_label: JsonLiteral | None = Field(
        serialization_alias="Dataset.versionLabel",
        default=None,
    )
    visibility: Visibility | None = Field(default=None, serialization_alias="Dataset.visibility")

    @field_serializer("status")
    def serialize_status(self, v: DatasetStatus) -> str:
        return f"https://openml.org/mldcatap/mldcat-ap/dataset-status#{v}"

    @field_serializer("visibility")
    def serialize_visibility(self, v: Visibility) -> str:
        return f"https://openml.org/mldcatap/mldcat-ap/dataset-visibility#{v}"


class DataService(JsonLDObject):
    type_: Literal["DataService"] = Field(default="DataService", serialization_alias="@type")
    endpoint_url: HttpUrl = Field(serialization_alias="DataService.endpointUrl")
    title: list[JsonLiteral] = Field(
        default_factory=list,
        min_length=1,
        serialization_alias="DataService.title",
    )
    serves_dataset: list[JsonLDObjectReference[Dataset]] = Field(
        default_factory=list,
        serialization_alias="DataService.servesDataset",
    )


# We need at least one forward reference for type annotation in the cycle
# `Dataset->Distribution->Dataservice->Dataset`, but this is not supported by
# the OpenAI schema checker, so we need to explicitly update the references.
Distribution.model_rebuild()


class JsonLDGraph(BaseModel):
    context: str | dict[str, HttpUrl] = Field(
        default_factory=lambda: {}, serialization_alias="@context"
    )
    graph: list[Distribution | DataService | Dataset | Quality | Feature | Agent | MD5Checksum] = (
        Field(default_factory=list, serialization_alias="@graph")
    )

    model_config = {"populate_by_name": True, "extra": "forbid"}
