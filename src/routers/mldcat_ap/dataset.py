"""Router for MLDCAT-AP endpoints: https://semiceu.github.io/MLDCAT-AP/releases/1.0.0/#examples

Incredibly inefficient, but it's just a proof of concept.
Specific queries could be written to fetch e.g., a single feature or quality.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection

import config
from database.users import User
from routers.dependencies import expdb_connection, fetch_user, userdb_connection
from routers.openml.datasets import get_dataset, get_dataset_features
from routers.openml.qualities import get_qualities
from schemas.datasets.mldcat_ap import (
    DataService,
    Dataset,
    Distribution,
    Feature,
    JsonLDGraph,
    JsonLDObjectReference,
    JsonLDQualifiedLiteral,
    MD5Checksum,
    Quality,
)

router = APIRouter(prefix="/mldcat_ap", tags=["MLDCAT-AP"])
_configuration = config.load_configuration()
_server_url = (
    f"{_configuration['arff_base_url']}{_configuration['fastapi']['root_path']}{router.prefix}"
)


@router.get(
    path="/distribution/{distribution_id}",
    description="Get meta-data for distribution with ID `distribution_id`.",
)
def get_mldcat_ap_distribution(
    distribution_id: int,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    user_db: Annotated[Connection, Depends(userdb_connection)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> JsonLDGraph:
    oml_dataset = get_dataset(
        dataset_id=distribution_id,
        user=user,
        user_db=user_db,
        expdb_db=expdb,
    )
    openml_features = get_dataset_features(distribution_id, user, expdb)
    features = [
        Feature(
            id_=f"{_server_url}/feature/{distribution_id}/{feature.index}",
            name=feature.name,
            feature_type=f"{_server_url}/schema/feature-type#{feature.data_type}",
        )
        for feature in openml_features
    ]
    oml_qualities = get_qualities(distribution_id, user, expdb)
    qualities = [
        Quality(
            id_=f"{_server_url}/quality/{quality.name}/{distribution_id}",
            quality_type=f"{_server_url}/quality/{quality.name}",
            value=str(quality.value),
        )
        for quality in oml_qualities
    ]
    checksum = MD5Checksum(
        id_=f"{_server_url}/checksum/{distribution_id}",
        value=oml_dataset.md5_checksum,
    )
    arff_service = DataService(
        id_=f"{_server_url}/dataservice/1",
        endpoint_url=_server_url,
        title=["REST API for sharing OpenML metadata in MLDCAT-AP format."],
    )
    distribution = Distribution(
        id_=f"{_server_url}/distribution/{distribution_id}",
        access_url=[f"https://www.openml.org/d/{distribution_id}"],
        has_feature=[JsonLDObjectReference[Feature].to(feature) for feature in features],
        has_quality=[JsonLDObjectReference[Quality].to(quality) for quality in qualities],
        default_target_attribute=next(iter(oml_dataset.default_target_attribute), None),
        download_url=[oml_dataset.url],
        format_=oml_dataset.format_,
        checksum=JsonLDObjectReference[MD5Checksum].to(checksum),
        access_service=[JsonLDObjectReference[DataService].to(arff_service)],
    )
    mldcat_dataset = Dataset(
        id_=str(distribution_id),
        type_="Dataset",
        collection_date=str(oml_dataset.upload_date),
        description=[oml_dataset.description],
        title=[oml_dataset.name],
        distribution=[JsonLDObjectReference[Distribution].to(distribution)],
        status=oml_dataset.status,
        version_info=str(oml_dataset.version),
        version_label=oml_dataset.version_label,
        visibility=oml_dataset.visibility,
        keyword=oml_dataset.tags,
        issued=JsonLDQualifiedLiteral(
            value=str(oml_dataset.upload_date),
            type_="http://www.w3.org/2001/XMLSchema#dateTime",
        ),
    )
    return JsonLDGraph(
        context="https://semiceu.github.io/MLDCAT-AP/releases/1.0.0/context.jsonld",
        graph=[
            mldcat_dataset,
            distribution,
            arff_service,
            checksum,
        ],
    )


@router.get(
    path="/dataservice/{service_id}",
    description="Get meta-data for a specific data service.",
)
def get_dataservice(service_id: int) -> JsonLDGraph:
    if service_id != 1:
        raise HTTPException(status_code=404, detail="Service not found.")
    return JsonLDGraph(
        context="https://semiceu.github.io/MLDCAT-AP/releases/1.0.0/context.jsonld",
        graph=[
            DataService(
                id_=f"{_server_url}/dataservice/{service_id}",
                endpoint_url=_server_url,
                title=["REST API for sharing OpenML metadata in MLDCAT-AP format."],
            ),
        ],
    )


@router.get(
    path="/quality/{quality_name}/{distribution_id}",
    description="Get meta-data for a specific quality and distribution.",
)
def get_distribution_quality(
    quality_name: str,
    distribution_id: int,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> JsonLDGraph:
    qualities = get_qualities(distribution_id, user, expdb)
    quality = next(q for q in qualities if q.name == quality_name)
    example_quality = Quality(
        id_=f"{_server_url}/quality/{quality_name}/{distribution_id}",
        quality_type=f"{_server_url}/quality/{quality_name}",
        value=str(quality.value),
    )

    return JsonLDGraph(
        context="https://semiceu.github.io/MLDCAT-AP/releases/1.0.0/context.jsonld",
        graph=[
            example_quality,
        ],
    )


@router.get(
    path="/feature/{distribution_id}/{feature_no}",
    description="Get meta-data for the n-th feature of a distribution.",
)
def get_distribution_feature(
    distribution_id: int,
    feature_no: int,
    user: Annotated[Connection, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> JsonLDGraph:
    features = get_dataset_features(
        dataset_id=distribution_id,
        user=user,
        expdb=expdb,
    )
    feature = features[feature_no]
    mldcat_feature = Feature(
        id_=f"{_server_url}/feature/{distribution_id}/{feature.index}",
        name=feature.name,
        feature_type=f"{_server_url}/schema/feature-type#{feature.data_type}",
    )
    return JsonLDGraph(
        context="https://semiceu.github.io/MLDCAT-AP/releases/1.0.0/context.jsonld",
        graph=[
            mldcat_feature,
        ],
    )
