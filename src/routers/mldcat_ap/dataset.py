"""Router for MLDCAT-AP endpoints: https://semiceu.github.io/MLDCAT-AP/releases/1.0.0/#examples"""

from typing import Annotated

from fastapi import APIRouter, Depends
from schemas.datasets.mldcat_ap import (
    DataService,
    Distribution,
    Feature,
    JsonLDGraph,
    JsonLDObjectReference,
    MD5Checksum,
    Quality,
    QualityType,
    convert_feature_to_mldcat_ap,
    convert_to_mldcat_ap,
)
from sqlalchemy import Connection

from routers.dependencies import expdb_connection, fetch_user, userdb_connection
from routers.openml.datasets import get_dataset, get_dataset_features

router = APIRouter(prefix="/mldcat_ap", tags=["MLDCAT-AP"])


@router.get(
    path="/dataset/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_mldcat_ap_dataset(
    dataset_id: int,
    user: Annotated[Connection, Depends(fetch_user)] = None,
    user_db: Annotated[Connection, Depends(userdb_connection)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> JsonLDGraph:
    dataset = get_dataset(
        dataset_id=dataset_id,
        user=user,
        user_db=user_db,
        expdb_db=expdb,
    )
    openml_features = get_dataset_features(dataset_id, user, expdb)
    features = [convert_feature_to_mldcat_ap(dataset_id, feature) for feature in openml_features]
    example_quality = Quality(
        id_="example-quality",
        quality_type=QualityType(
            id_="quality-type-example",
            name="number_of_features",
            quality_id="link_to_definition",
        ),
        value="150",
    )
    checksum = MD5Checksum(id_="checksum-id", value=dataset.md5_checksum)
    arff_service = DataService(
        id_="openml-arff-service",
        title=["OpenML ARFF server"],
        endpoint_url="https://www.openml.org/data/download",
    )
    distribution = Distribution(
        id_="distribution-id",
        access_url=[f"https://www.openml.org/d/{dataset_id}"],
        has_feature=[JsonLDObjectReference[Feature].to(feature) for feature in features],
        has_quality=[JsonLDObjectReference[Quality].to(example_quality)],
        default_target_attribute=next(iter(dataset.default_target_attribute), None),
        download_url=[dataset.url],
        format_=dataset.format_,
        checksum=JsonLDObjectReference[MD5Checksum].to(checksum),
        access_service=[JsonLDObjectReference[DataService].to(arff_service)],
    )
    return JsonLDGraph(
        context="https://semiceu.github.io/MLDCAT-AP/releases/1.0.0/context.jsonld",
        graph=[
            distribution,
            arff_service,
            checksum,
        ],
    )


@router.get(
    path="/dataservice/{service_id}",
    description="Get meta-data for a specific data service.",
)
def get_dataservice(
    dataset_id: int,
    user_db: Annotated[Connection, Depends(userdb_connection)] = None,
    expdb_db: Annotated[Connection, Depends(expdb_connection)] = None,
) -> JsonLDGraph:
    openml_dataset = get_dataset(
        dataset_id=dataset_id,
        user_db=user_db,
        expdb_db=expdb_db,
    )
    return convert_to_mldcat_ap(openml_dataset)


@router.get(
    path="/quality/{quality_name}/{distribution_id}",
    description="Get meta-data for a specific quality and distribution.",
)
def get_distribution_quality(
    dataset_id: int,
    user: Annotated[Connection, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> JsonLDGraph:
    openml_dataset = get_dataset(
        dataset_id=dataset_id,
        user=user,
        expdb_db=expdb,
    )
    return convert_to_mldcat_ap(openml_dataset)


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
    mldcat_feature = convert_feature_to_mldcat_ap(
        distribution_id,
        features[feature_no],
    )
    return JsonLDGraph(
        context="https://semiceu.github.io/MLDCAT-AP/releases/1.0.0/context.jsonld",
        graph=[
            mldcat_feature,
        ],
    )
