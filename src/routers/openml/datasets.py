"""
We add separate endpoints for old-style JSON responses, so they don't clutter the schema of the
new API, and are easily removed later.
"""
import http.client
import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, NamedTuple

from core.access import _user_has_access
from core.errors import DatasetError
from core.formatting import (
    _csv_as_list,
    _format_dataset_url,
    _format_error,
    _format_parquet_url,
    _safe_unquote,
)
from database.datasets import get_dataset as db_get_dataset
from database.datasets import (
    get_feature_values,
    get_features_for_dataset,
    get_file,
    get_latest_dataset_description,
    get_latest_processing_update,
    get_latest_status_update,
    get_qualities_for_datasets,
    get_tags,
)
from database.datasets import tag_dataset as db_tag_dataset
from database.users import User, UserGroup
from fastapi import APIRouter, Body, Depends, HTTPException
from schemas.datasets.openml import DatasetMetadata, DatasetStatus, Feature, FeatureType
from sqlalchemy import Connection, text

from routers.dependencies import Pagination, expdb_connection, fetch_user, userdb_connection
from routers.types import CasualString128, IntegerRange, SystemString64, integer_range_regex

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    path="/tag",
)
def tag_dataset(
    data_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb_db: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[str, dict[str, Any]]:
    tags = get_tags(data_id, expdb_db)
    if tag.casefold() in [t.casefold() for t in tags]:
        raise HTTPException(
            status_code=http.client.INTERNAL_SERVER_ERROR,
            detail={
                "code": "473",
                "message": "Entity already tagged by this tag.",
                "additional_information": f"id={data_id}; tag={tag}",
            },
        )

    if user is None:
        raise HTTPException(
            status_code=http.client.PRECONDITION_FAILED,
            detail={"code": "103", "message": "Authentication failed"},
        ) from None
    db_tag_dataset(user.user_id, data_id, tag, connection=expdb_db)
    all_tags = [*tags, tag]
    tag_value = all_tags if len(all_tags) > 1 else all_tags[0]

    return {
        "data_tag": {"id": str(data_id), "tag": tag_value},
    }


class DatasetStatusFilter(StrEnum):
    ACTIVE = DatasetStatus.ACTIVE
    DEACTIVATED = DatasetStatus.DEACTIVATED
    IN_PREPARATION = DatasetStatus.IN_PREPARATION
    ALL = "all"


@router.post(path="/list", description="Provided for convenience, same as `GET` endpoint.")
@router.get(path="/list")
def list_datasets(
    pagination: Annotated[Pagination, Body(default_factory=Pagination)],
    data_name: Annotated[str | None, CasualString128] = None,
    tag: Annotated[str | None, SystemString64] = None,
    data_version: Annotated[
        int | None,
        Body(description="The dataset version to include in the search."),
    ] = None,
    uploader: Annotated[
        int | None,
        Body(description="User id of the uploader whose datasets to include in the search."),
    ] = None,
    data_id: Annotated[
        list[int] | None,
        Body(
            description="The dataset(s) to include in the search. "
            "If none are specified, all datasets are included.",
        ),
    ] = None,
    number_instances: Annotated[str | None, IntegerRange] = None,
    number_features: Annotated[str | None, IntegerRange] = None,
    number_classes: Annotated[str | None, IntegerRange] = None,
    number_missing_values: Annotated[str | None, IntegerRange] = None,
    status: Annotated[DatasetStatusFilter, Body()] = DatasetStatusFilter.ACTIVE,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb_db: Annotated[Connection, Depends(expdb_connection)] = None,
) -> list[dict[str, Any]]:
    current_status = text(
        """
        SELECT ds1.`did`, ds1.`status`
        FROM dataset_status as ds1
        WHERE ds1.`status_date`=(
            SELECT MAX(ds2.`status_date`)
            FROM dataset_status as ds2
            WHERE ds1.`did`=ds2.`did`
        )
        """,
    )

    if status == DatasetStatusFilter.ALL:
        statuses = [
            DatasetStatusFilter.ACTIVE,
            DatasetStatusFilter.DEACTIVATED,
            DatasetStatusFilter.IN_PREPARATION,
        ]
    else:
        statuses = [status]

    where_status = ",".join(f"'{status}'" for status in statuses)
    if user is None:
        visible_to_user = "`visibility`='public'"
    elif UserGroup.ADMIN in user.groups:
        visible_to_user = "TRUE"
    else:
        visible_to_user = f"(`visibility`='public' OR `uploader`={user.user_id})"

    where_name = "" if data_name is None else "AND `name`=:data_name"
    where_version = "" if data_version is None else "AND `version`=:data_version"
    where_uploader = "" if uploader is None else "AND `uploader`=:uploader"
    data_id_str = ",".join(str(did) for did in data_id) if data_id else ""
    where_data_id = "" if not data_id else f"AND d.`did` IN ({data_id_str})"

    # requires some benchmarking on whether e.g., IN () is more efficient.
    matching_tag = (
        text(
            """
        AND d.`did` IN (
            SELECT `id`
            FROM dataset_tag as dt
            WHERE dt.`tag`=:tag
        )
        """,
        )
        if tag
        else ""
    )

    def quality_clause(quality: str, range_: str | None) -> str:
        if not range_:
            return ""
        if not (match := re.match(integer_range_regex, range_)):
            msg = f"`range_` not a valid range: {range_}"
            raise ValueError(msg)
        start, end = match.groups()
        value = f"`value` BETWEEN {start} AND {end[2:]}" if end else f"`value`={start}"
        return f""" AND
            d.`did` IN (
                SELECT `data`
                FROM data_quality
                WHERE `quality`='{quality}' AND {value}
            )
        """  # nosec  - `quality` is not user provided, value is filtered with regex

    number_instances_filter = quality_clause("NumberOfInstances", number_instances)
    number_classes_filter = quality_clause("NumberOfClasses", number_classes)
    number_features_filter = quality_clause("NumberOfFeatures", number_features)
    number_missing_values_filter = quality_clause("NumberOfMissingValues", number_missing_values)
    matching_filter = text(
        f"""
        SELECT d.`did`,d.`name`,d.`version`,d.`format`,d.`file_id`,
               IFNULL(cs.`status`, 'in_preparation')
        FROM dataset AS d
        LEFT JOIN ({current_status}) AS cs ON d.`did`=cs.`did`
        WHERE {visible_to_user} {where_name} {where_version} {where_uploader}
        {where_data_id} {matching_tag} {number_instances_filter} {number_features_filter}
        {number_classes_filter} {number_missing_values_filter}
        AND IFNULL(cs.`status`, 'in_preparation') IN ({where_status})
        LIMIT {pagination.limit} OFFSET {pagination.offset}
        """,  # nosec
        # I am not sure how to do this correctly without an error from Bandit here.
        # However, the `status` input is already checked by FastAPI to be from a set
        # of given options, so no injection is possible (I think). The `current_status`
        # subquery also has no user input. So I think this should be safe.
    )
    columns = ["did", "name", "version", "format", "file_id", "status"]
    rows = expdb_db.execute(
        matching_filter,
        parameters={
            "tag": tag,
            "data_name": data_name,
            "data_version": data_version,
            "uploader": uploader,
        },
    )
    datasets: dict[int, dict[str, Any]] = {
        row.did: dict(zip(columns, row, strict=True)) for row in rows
    }
    if not datasets:
        raise HTTPException(
            status_code=http.client.PRECONDITION_FAILED,
            detail={"code": "372", "message": "No results"},
        ) from None

    for dataset in datasets.values():
        # The old API does not actually provide the checksum but just an empty field
        dataset["md5_checksum"] = ""
        dataset["quality"] = []
        dataset["version"] = int(dataset["version"])

    # The method of filtering and adding the qualities information is the same to
    # how it was done in PHP. Something like a pivot table seems more reasonable
    # to me. Pivot tables dont seem well supported though, would need to benchmark
    # doing it in the DB probably with some view or many joins.
    qualities_to_show = [
        "MajorityClassSize",
        "MaxNominalAttDistinctValues",
        "MinorityClassSize",
        "NumberOfClasses",
        "NumberOfFeatures",
        "NumberOfInstances",
        "NumberOfInstancesWithMissingValues",
        "NumberOfMissingValues",
        "NumberOfNumericFeatures",
        "NumberOfSymbolicFeatures",
    ]
    qualities_by_dataset = get_qualities_for_datasets(
        dataset_ids=datasets.keys(),
        qualities=qualities_to_show,
        connection=expdb_db,
    )
    for did, qualities in qualities_by_dataset.items():
        datasets[did]["quality"] = qualities
    return list(datasets.values())


class ProcessingInformation(NamedTuple):
    date: datetime | None
    warning: str | None
    error: str | None


def _get_processing_information(dataset_id: int, connection: Connection) -> ProcessingInformation:
    """Return processing information, if any. Otherwise, all fields `None`."""
    if not (data_processed := get_latest_processing_update(dataset_id, connection)):
        return ProcessingInformation(date=None, warning=None, error=None)

    date_processed = data_processed["processing_date"]
    warning = data_processed["warning"].strip() if data_processed["warning"] else None
    error = data_processed["error"].strip() if data_processed["error"] else None
    return ProcessingInformation(date=date_processed, warning=warning, error=error)


def _get_dataset_raise_otherwise(
    dataset_id: int,
    user: User | None,
    expdb: Connection,
) -> dict[str, Any]:
    """Fetches the dataset from the database if it exists and the user has permissions.

    Raises HTTPException if the dataset does not exist or the user can not access it.
    """
    if not (dataset := db_get_dataset(dataset_id, expdb)):
        error = _format_error(code=DatasetError.NOT_FOUND, message="Unknown dataset")
        raise HTTPException(status_code=http.client.NOT_FOUND, detail=error)

    if not _user_has_access(dataset=dataset, user=user):
        error = _format_error(code=DatasetError.NO_ACCESS, message="No access granted")
        raise HTTPException(status_code=http.client.FORBIDDEN, detail=error)

    return dataset


@router.get("/features/{dataset_id}", response_model_exclude_none=True)
def get_dataset_features(
    dataset_id: int,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> list[Feature]:
    _get_dataset_raise_otherwise(dataset_id, user, expdb)
    features = get_features_for_dataset(dataset_id, expdb)
    for feature in [f for f in features if f.data_type == FeatureType.NOMINAL]:
        feature.nominal_values = get_feature_values(dataset_id, feature.index, expdb)

    if not features:
        processing_state = get_latest_processing_update(dataset_id, expdb)
        if processing_state is None:
            code, msg = (
                273,
                "Dataset not processed yet. The dataset was not processed yet, features are not yet available. Please wait for a few minutes.",  # noqa: E501
            )
        elif processing_state.get("error"):
            code, msg = 274, "No features found. Additionally, dataset processed with error"
        else:
            code, msg = (
                272,
                "No features found. The dataset did not contain any features, or we could not extract them.",  # noqa: E501
            )
        raise HTTPException(
            status_code=http.client.PRECONDITION_FAILED,
            detail={"code": code, "message": msg},
        )
    return features


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_dataset(
    dataset_id: int,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    user_db: Annotated[Connection, Depends(userdb_connection)] = None,
    expdb_db: Annotated[Connection, Depends(expdb_connection)] = None,
) -> DatasetMetadata:
    dataset = _get_dataset_raise_otherwise(dataset_id, user, expdb_db)
    if not (dataset_file := get_file(dataset["file_id"], user_db)):
        error = _format_error(
            code=DatasetError.NO_DATA_FILE,
            message="No data file found",
        )
        raise HTTPException(status_code=http.client.PRECONDITION_FAILED, detail=error)

    tags = get_tags(dataset_id, expdb_db)
    description = get_latest_dataset_description(dataset_id, expdb_db)
    processing_result = _get_processing_information(dataset_id, expdb_db)
    status = get_latest_status_update(dataset_id, expdb_db)

    status_ = DatasetStatus(status["status"]) if status else DatasetStatus.IN_PREPARATION

    description_ = ""
    if description:
        description_ = description["description"].replace("\r", "").strip()

    dataset_url = _format_dataset_url(dataset)
    parquet_url = _format_parquet_url(dataset)

    contributors = _csv_as_list(dataset["contributor"], unquote_items=True)
    creators = _csv_as_list(dataset["creator"], unquote_items=True)
    ignore_attribute = _csv_as_list(dataset["ignore_attribute"], unquote_items=True)
    row_id_attribute = _csv_as_list(dataset["row_id_attribute"], unquote_items=True)
    original_data_url = _csv_as_list(dataset["original_data_url"], unquote_items=True)

    # Not sure which properties are set by this bit:
    # foreach( $this->xml_fields_dataset['csv'] as $field ) {
    #   $dataset->{$field} = getcsv( $dataset->{$field} );
    # }

    return DatasetMetadata(
        id=dataset["did"],
        visibility=dataset["visibility"],
        status=status_,
        name=dataset["name"],
        licence=dataset["licence"],
        version=dataset["version"],
        version_label=dataset["version_label"] or "",
        language=dataset["language"] or "",
        creator=creators,
        contributor=contributors,
        citation=dataset["citation"] or "",
        upload_date=dataset["upload_date"],
        processing_date=processing_result.date,
        warning=processing_result.warning,
        error=processing_result.error,
        description=description_,
        description_version=description["version"] if description else 0,
        tag=tags,
        default_target_attribute=_safe_unquote(dataset["default_target_attribute"]),
        ignore_attribute=ignore_attribute,
        row_id_attribute=row_id_attribute,
        url=dataset_url,
        parquet_url=parquet_url,
        minio_url=parquet_url,
        file_id=dataset["file_id"],
        format=dataset["format"].lower(),
        paper_url=dataset["paper_url"] or None,
        original_data_url=original_data_url,
        collection_date=dataset["collection_date"],
        md5_checksum=dataset_file["md5_hash"],
    )
