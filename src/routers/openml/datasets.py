import re
from datetime import datetime
from enum import StrEnum
from http import HTTPStatus
from typing import Annotated, Any, Literal, NamedTuple

from fastapi import APIRouter, Body, Depends
from sqlalchemy import Connection, text
from sqlalchemy.engine import Row

import database.datasets
import database.qualities
from core.access import _user_has_access
from core.errors import DatasetError, ProblemType, raise_problem
from core.formatting import (
    _csv_as_list,
    _format_dataset_url,
    _format_parquet_url,
)
from database.users import User, UserGroup
from routers.dependencies import Pagination, expdb_connection, fetch_user, userdb_connection
from routers.types import CasualString128, IntegerRange, SystemString64, integer_range_regex
from schemas.datasets.openml import DatasetMetadata, DatasetStatus, Feature, FeatureType

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
    tags = database.datasets.get_tags_for(data_id, expdb_db)
    if tag.casefold() in [t.casefold() for t in tags]:
        raise_problem(
            status_code=HTTPStatus.CONFLICT,
            type_=ProblemType.TAG_ALREADY_EXISTS,
            detail=f"Entity already tagged by this tag. id={data_id}; tag={tag}",
            code=473,
        )

    if user is None:
        raise_problem(
            status_code=HTTPStatus.UNAUTHORIZED,
            type_=ProblemType.AUTHENTICATION_FAILED,
            detail="Authentication failed.",
            code=103,
        )

    database.datasets.tag(data_id, tag, user_id=user.user_id, connection=expdb_db)
    return {
        "data_tag": {"id": str(data_id), "tag": [*tags, tag]},
    }


class DatasetStatusFilter(StrEnum):
    ACTIVE = DatasetStatus.ACTIVE
    DEACTIVATED = DatasetStatus.DEACTIVATED
    IN_PREPARATION = DatasetStatus.IN_PREPARATION
    ALL = "all"


@router.post(path="/list", description="Provided for convenience, same as `GET` endpoint.")
@router.get(path="/list")
def list_datasets(  # noqa: PLR0913
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
        """  # noqa: S608 - `quality` is not user provided, value is filtered with regex

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
        """,  # noqa: S608
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
        raise_problem(
            status_code=HTTPStatus.NOT_FOUND,
            type_=ProblemType.NO_RESULTS,
            detail="No datasets match the search criteria.",
            code=372,
        )

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
    qualities_by_dataset = database.qualities.get_for_datasets(
        dataset_ids=datasets.keys(),
        quality_names=qualities_to_show,
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
    if not (
        data_processed := database.datasets.get_latest_processing_update(dataset_id, connection)
    ):
        return ProcessingInformation(date=None, warning=None, error=None)

    date_processed = data_processed.processing_date
    warning = data_processed.warning.strip() if data_processed.warning else None
    error = data_processed.error.strip() if data_processed.error else None
    return ProcessingInformation(date=date_processed, warning=warning, error=error)


def _get_dataset_raise_otherwise(
    dataset_id: int,
    user: User | None,
    expdb: Connection,
) -> Row:
    """Fetches the dataset from the database if it exists and the user has permissions.

    Raises ProblemDetailException if the dataset does not exist or the user can not access it.
    """
    if not (dataset := database.datasets.get(dataset_id, expdb)):
        raise_problem(
            status_code=HTTPStatus.NOT_FOUND,
            type_=ProblemType.DATASET_NOT_FOUND,
            detail="Unknown dataset.",
            code=DatasetError.NOT_FOUND,
        )

    if not _user_has_access(dataset=dataset, user=user):
        raise_problem(
            status_code=HTTPStatus.FORBIDDEN,
            type_=ProblemType.DATASET_NO_ACCESS,
            detail="No access granted.",
            code=DatasetError.NO_ACCESS,
        )

    return dataset


@router.get("/features/{dataset_id}", response_model_exclude_none=True)
def get_dataset_features(
    dataset_id: int,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> list[Feature]:
    _get_dataset_raise_otherwise(dataset_id, user, expdb)
    features = database.datasets.get_features(dataset_id, expdb)
    for feature in [f for f in features if f.data_type == FeatureType.NOMINAL]:
        feature.nominal_values = database.datasets.get_feature_values(
            dataset_id,
            feature_index=feature.index,
            connection=expdb,
        )

    if not features:
        processing_state = database.datasets.get_latest_processing_update(dataset_id, expdb)
        if processing_state is None:
            raise_problem(
                status_code=HTTPStatus.PRECONDITION_FAILED,
                type_=ProblemType.DATASET_NOT_PROCESSED,
                detail=(
                    "Dataset not processed yet. The dataset was not processed yet, "
                    "features are not yet available. Please wait for a few minutes."
                ),
                code=273,
            )
        elif processing_state.error:
            raise_problem(
                status_code=HTTPStatus.PRECONDITION_FAILED,
                type_=ProblemType.DATASET_PROCESSING_ERROR,
                detail="No features found. Additionally, dataset processed with error.",
                code=274,
            )
        else:
            raise_problem(
                status_code=HTTPStatus.PRECONDITION_FAILED,
                type_=ProblemType.DATASET_NO_FEATURES,
                detail=(
                    "No features found. "
                    "The dataset did not contain any features, or we could not extract them."
                ),
                code=272,
            )
    return features


@router.post(
    path="/status/update",
)
def update_dataset_status(
    dataset_id: Annotated[int, Body()],
    status: Annotated[Literal[DatasetStatus.ACTIVE, DatasetStatus.DEACTIVATED], Body()],
    user: Annotated[User | None, Depends(fetch_user)],
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> dict[str, str | int]:
    if user is None:
        raise_problem(
            status_code=HTTPStatus.UNAUTHORIZED,
            type_=ProblemType.AUTHENTICATION_REQUIRED,
            detail="Updating dataset status requires authentication.",
        )

    dataset = _get_dataset_raise_otherwise(dataset_id, user, expdb)

    can_deactivate = dataset.uploader == user.user_id or UserGroup.ADMIN in user.groups
    if status == DatasetStatus.DEACTIVATED and not can_deactivate:
        raise_problem(
            status_code=HTTPStatus.FORBIDDEN,
            type_=ProblemType.DATASET_NOT_OWNED,
            detail="Dataset is not owned by you.",
            code=693,
        )
    if status == DatasetStatus.ACTIVE and UserGroup.ADMIN not in user.groups:
        raise_problem(
            status_code=HTTPStatus.FORBIDDEN,
            type_=ProblemType.DATASET_ADMIN_ONLY,
            detail="Only administrators can activate datasets.",
            code=696,
        )

    current_status = database.datasets.get_status(dataset_id, expdb)
    if current_status and current_status.status == status:
        raise_problem(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            type_=ProblemType.DATASET_STATUS_TRANSITION,
            detail="Illegal status transition.",
            code=694,
        )

    # If current status is unknown, it is effectively "in preparation",
    # So the following transitions are allowed (first 3 transitions are first clause)
    #  - in preparation => active  (add a row)
    #  - in preparation => deactivated  (add a row)
    #  - active => deactivated  (add a row)
    #  - deactivated => active  (delete a row)
    if current_status is None or status == DatasetStatus.DEACTIVATED:
        database.datasets.update_status(dataset_id, status, user_id=user.user_id, connection=expdb)
    elif current_status.status == DatasetStatus.DEACTIVATED:
        database.datasets.remove_deactivated_status(dataset_id, expdb)
    else:
        raise_problem(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            type_=ProblemType.INTERNAL_ERROR,
            detail=f"Unknown status transition: {current_status} -> {status}",
        )

    return {"dataset_id": dataset_id, "status": status}


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
    if not (
        dataset_file := database.datasets.get_file(file_id=dataset.file_id, connection=user_db)
    ):
        raise_problem(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            type_=ProblemType.DATASET_NO_DATA_FILE,
            detail="No data file found.",
            code=DatasetError.NO_DATA_FILE,
        )

    tags = database.datasets.get_tags_for(dataset_id, expdb_db)
    description = database.datasets.get_description(dataset_id, expdb_db)
    processing_result = _get_processing_information(dataset_id, expdb_db)
    status = database.datasets.get_status(dataset_id, expdb_db)

    status_ = DatasetStatus(status.status) if status else DatasetStatus.IN_PREPARATION

    description_ = ""
    if description:
        description_ = description.description.replace("\r", "").strip()

    dataset_url = _format_dataset_url(dataset)
    parquet_url = _format_parquet_url(dataset)

    contributors = _csv_as_list(dataset.contributor, unquote_items=True)
    creators = _csv_as_list(dataset.creator, unquote_items=True)
    ignore_attribute = _csv_as_list(dataset.ignore_attribute, unquote_items=True)
    row_id_attribute = _csv_as_list(dataset.row_id_attribute, unquote_items=True)
    original_data_url = _csv_as_list(dataset.original_data_url, unquote_items=True)
    default_target_attribute = _csv_as_list(dataset.default_target_attribute, unquote_items=True)

    return DatasetMetadata(
        id=dataset.did,
        visibility=dataset.visibility,
        status=status_,
        name=dataset.name,
        licence=dataset.licence,
        version=dataset.version,
        version_label=dataset.version_label or "",
        language=dataset.language or "",
        creator=creators,
        contributor=contributors,
        citation=dataset.citation or "",
        upload_date=dataset.upload_date,
        processing_date=processing_result.date,
        warning=processing_result.warning,
        error=processing_result.error,
        description=description_,
        description_version=description.version if description else 0,
        tag=tags,
        default_target_attribute=default_target_attribute,
        ignore_attribute=ignore_attribute,
        row_id_attribute=row_id_attribute,
        url=dataset_url,
        parquet_url=parquet_url,
        file_id=dataset.file_id,
        format=dataset.format.lower(),
        paper_url=dataset.paper_url or None,
        original_data_url=original_data_url,
        collection_date=dataset.collection_date,
        md5_checksum=dataset_file.md5_hash,
    )
