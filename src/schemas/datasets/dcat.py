"""
This file is copied over from an external source.
Original Author: Jos van der Velde
Source: https://github.com/aiondemand/AIOD-rest-api/blob/develop/src/converters/schema/dcat.py
License: MIT

Based on DCAT Application Profile for data portals in Europe Version 2.1.1

The DCAT Application Profile for data portals in Europe (DCAT-AP) is a specification
based on W3C's Data Catalogue vocabulary (DCAT) for describing public sector datasets
in Europe. Its basic use case is to enable a cross-data portal search for datasets and
make public sector data better searchable across borders and sectors. This can be
achieved by the exchange of descriptions of data sets among data portals.
"""
import datetime
from abc import ABC
from typing import Union

from pydantic import BaseModel, Field


class DcatAPContext(BaseModel):
    dcat: str = Field(default="http://www.w3.org/ns/dcat", const=True)
    dct: str = Field(default="https://purl.org/dc/terms/", const=True)
    vcard: str = Field(default="https://www.w3.org/2006/vcard/ns#", const=True)


class DcatAPObject(BaseModel, ABC):
    """Base class for all DCAT-AP objects"""

    id_: str = Field(serialization_alias="@id")

    model_config = {"populate_by_name": True, "extra": "forbid"}


class DcatAPIdentifier(DcatAPObject):
    """Identifying another DcatAPObject. Contains only an id."""


class VCardIndividual(DcatAPObject):
    type_: str = Field(default="vcard:Individual", serialization_alias="@type", const=True)
    fn: str = Field(
        serialization_alias="vcard:fn",
        description="The formatted text corresponding to the name of the object",
    )


class VCardOrganisation(DcatAPObject):
    type_: str = Field(default="vcard:Organisation", serialization_alias="@type", const=True)
    fn: str = Field(
        serialization_alias="vcard:fn",
        description="The formatted text corresponding to the name of the object",
    )


class DcatLocation(DcatAPObject):
    type_: str = Field(default="dct:Location", serialization_alias="@type", const=True)
    bounding_box: str | None = Field(serialization_alias="dcat:bbox", default=None)
    centroid: str | None = Field(serialization_alias="dcat:centroid", default=None)
    geometry: str | None = Field(serialization_alias="dcat:geometry", default=None)


class SpdxChecksum(DcatAPObject):
    type_: str = Field(default="spdx:Checksum", serialization_alias="@type", const=True)
    algorithm: str = Field(serialization_alias="spdx:algorithm")
    value: str = Field(serialization_alias="spdx:checksumValue")


class XSDDateTime(BaseModel):
    type_: str = Field(default="xsd:dateTime", serialization_alias="@type", const=True)
    value_: datetime.datetime | datetime.date = Field(serialization_alias="@value")

    model_config = {"populate_by_name": True, "extra": "forbid"}


class DctPeriodOfTime(DcatAPObject):
    type_: str = Field(default="dct:PeriodOfTime", serialization_alias="@type", const=True)
    start_date: XSDDateTime | None = Field(serialization_alias="dcat:startDate", default=None)
    end_date: XSDDateTime | None = Field(serialization_alias="dcat:endDate", default=None)


class DcatAPDistribution(DcatAPObject):
    type_: str = Field(default="dcat:Distribution", serialization_alias="@type", const=True)
    access_url: list[str] = Field(
        serialization_alias="dcat:accessURL",
        default_factory=list,
        min_items=1,
    )
    byte_size: int | None = Field(serialization_alias="dcat:byteSize", default=None)
    checksum: DcatAPIdentifier | None = Field(serialization_alias="spdx:checksum", default=None)
    description: list[str] = Field(serialization_alias="dct:description", default_factory=list)
    download_url: list[str] = Field(serialization_alias="dcat:downloadURL", default_factory=list)
    format_: str | None = Field(serialization_alias="dct:format", default=None)
    license_: str | None = Field(serialization_alias="dct:license", default=None)
    title: list[str] = Field(serialization_alias="dct:title", default_factory=list)


class DcatAPDataset(DcatAPObject):
    type_: str = Field(default="dcat:Dataset", serialization_alias="@type", const=True)
    description: list[str] = Field(
        serialization_alias="dct:description",
        description="A free-text account of the Dataset",
        default_factory=list,
        min_items=1,
    )
    title: list[str] = Field(
        serialization_alias="dct:title",
        description="The name given to the Dataset",
        default_factory=list,
        min_items=1,
    )
    contact_point: list[DcatAPIdentifier] = Field(
        serialization_alias="dcat:contactPoint",
        description="Contact information to send comments about the Dataset to.",
        default_factory=list,
    )
    distribution: list[DcatAPIdentifier] = Field(
        serialization_alias="dcat:distribution",
        default_factory=list,
    )
    keyword: list[str] = Field(serialization_alias="dcat:keyword", default_factory=list)
    publisher: DcatAPIdentifier | None = Field(
        serialization_alias="dct:publisher",
        description="The entity (organisation) responsible for making the Dataset available.",
        default=None,
    )
    temporal_coverage: list[DcatAPIdentifier] = Field(
        serialization_alias="dct:temporal",
        description="The temporal period that the Dataset covers.",
        default_factory=list,
    )
    spatial_coverage: list[DcatAPIdentifier] = Field(
        serialization_alias="dct:spatial",
        description="The geographic region that is covered by the Dataset.",
        default_factory=list,
    )
    theme: list[str] = Field(
        serialization_alias="dcat:theme",
        description="Any categories that may be associated with the Dataset.",
        default_factory=list,
    )

    creator: list[DcatAPIdentifier] = Field(
        serialization_alias="dcat:creator",
        default_factory=list,
    )
    documentation: list[str] = Field(serialization_alias="foaf:page", default_factory=list)
    landing_page: list[str] = Field(
        serialization_alias="dcat:landingPage",
        description="The web page that provides access to "
        "the Dataset, its Distributions and/or additional information. "
        "It is intended to point to a landing page at the original data "
        "provider, not to a page on a site of a third party, "
        "such as an aggregator.",
        default_factory=list,
    )
    release_date: XSDDateTime | None = Field(serialization_alias="dct:issued", default=None)
    update_date: XSDDateTime | None = Field(serialization_alias="dct:modified", default=None)
    version: str | None = Field(serialization_alias="owl:versionInfo", default=None)


class DcatApWrapper(BaseModel):
    """The resulting class, containing a dataset and related entities in the graph"""

    context_: DcatAPContext = Field(
        default=DcatAPContext(),
        serialization_alias="@context",
        const=True,
    )
    # instead of list[DcatAPObject], a union with all the possible values is necessary.
    # See https://stackoverflow.com/questions/58301364/pydantic-and-subclasses-of-abstract-class
    graph_: list[
        Union[
            DcatAPDataset,
            DcatAPDistribution,
            DcatLocation,
            SpdxChecksum,
            VCardOrganisation,
            VCardIndividual,
            DctPeriodOfTime,
        ]
    ] = Field(serialization_alias="@graph")

    model_config = {"populate_by_name": True, "extra": "forbid"}
