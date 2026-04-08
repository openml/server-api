import asyncio
import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, NamedTuple

from fastapi import APIRouter, Body, Depends
from loguru import logger
from sqlalchemy import bindparam, text
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncConnection

import database.datasets
import database.qualities
from core.access import _user_has_access
from core.errors import (
    DatasetAdminOnlyError,
    DatasetNoAccessError,
    DatasetNoDataFileError,
    DatasetNoFeaturesError,
    DatasetNotFoundError,
    DatasetNotOwnedError,
    DatasetNotProcessedError,
    DatasetProcessingError,
    DatasetStatusTransitionError,
    InternalError,
    NoResultsError,
    TagAlreadyExistsError,
)
from core.formatting import (
    _csv_as_list,
    _format_dataset_url,
    _format_parquet_url,
)
from database.users import User
from routers.dependencies import (
    Pagination,
    expdb_connection,
    fetch_user,
    fetch_user_or_raise,
    userdb_connection,
)
from routers.types import CasualString128, IntegerRange, SystemString64, integer_range_regex
from schemas.datasets.openml import DatasetMetadata, DatasetStatus, Feature, FeatureType

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    path="/tag",
)
async def tag_dataset(
    data_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb_db: Annotated[AsyncConnection, Depends(expdb_connection)] = None,
) -> dict[str, dict[str, Any]]:
    assert expdb_db is not None  # noqa: S101
    tags = await database.datasets.get_tags_for(data_id, expdb_db)
    if tag.casefold() in [t.casefold() for t in tags]:
        msg = f"Dataset {data_id} already tagged with {tag!r}."
        raise TagAlreadyExistsError(msg)

    await database.datasets.tag(data_id, tag, user_id=user.user_id, connection=expdb_db)
    logger.info("Dataset {dataset_id} tagged '{tag}'.", dataset_id=data_id, tag=tag)
    return {
        "data_tag": {"id": str(data_id), "tag": [*tags, tag]},
    }


class DatasetStatusFilter(StrEnum):
    ACTIVE = DatasetStatus.ACTIVE
    DEACTIVATED = DatasetStatus.DEACTIVATED
    IN_PREPARATION = DatasetStatus.IN_PREPARATION
    ALL = "all"


def _quality_clause(quality: str, range_: str | None) -> str:
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


@router.post(path="/list", description="Provided for convenience, same as `GET` endpoint.")
@router.get(path="/list")
async def list_datasets(  # noqa: PLR0913, C901
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
    expdb_db: Annotated[AsyncConnection, Depends(expdb_connection)] = None,
) -> list[dict[str, Any]]:
    assert expdb_db is not None  # noqa: S101
    status_subquery = text(
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

    clauses = []
    parameters: dict[str, Any] = {
        "offset": pagination.offset,
        "limit": pagination.limit,
    }
    if status != DatasetStatusFilter.ALL:
        clauses.append("AND IFNULL(cs.`status`, 'in_preparation') = :status")
        parameters["status"] = status

    if user is None:
        clauses.append("AND `visibility`='public'")
    elif not await user.is_admin():
        clauses.append("AND (`visibility`='public' OR `uploader`=:user_id)")
        parameters["user_id"] = user.user_id

    if uploader:
        clauses.append("AND `uploader`=:uploader")
        parameters["uploader"] = uploader

    if data_name:
        clauses.append("AND `name`=:data_name")
        parameters["data_name"] = data_name

    if data_version:
        clauses.append("AND `version`=:data_version")
        parameters["data_version"] = data_version

    if data_id:
        clauses.append("AND d.`did` IN :data_ids")
        parameters["data_ids"] = data_id

    # requires some benchmarking on whether e.g., IN () is more efficient.
    if tag:
        clauses.append(
            """
            AND d.`did` IN (
                SELECT `id`
                FROM dataset_tag as dt
                WHERE dt.`tag`=:tag
            )
            """,
        )
        parameters["tag"] = tag

    number_instances_filter = _quality_clause("NumberOfInstances", number_instances)
    number_classes_filter = _quality_clause("NumberOfClasses", number_classes)
    number_features_filter = _quality_clause("NumberOfFeatures", number_features)
    number_missing_values_filter = _quality_clause("NumberOfMissingValues", number_missing_values)

    columns = ["did", "name", "version", "format", "file_id", "status"]
    matching_filter = text(
        f"""
        SELECT d.`did`,d.`name`,d.`version`,d.`format`,d.`file_id`,
               IFNULL(cs.`status`, 'in_preparation')
        FROM dataset AS d
        LEFT JOIN ({status_subquery}) AS cs ON d.`did`=cs.`did`
        WHERE 1=1 {number_instances_filter} {number_features_filter}
        {number_classes_filter} {number_missing_values_filter}
        {" ".join(clauses)}
        LIMIT :limit OFFSET :offset
        """,  # noqa: S608
        # I am not sure how to do this correctly without an error from Bandit here.
        # However, the `status` input is already checked by FastAPI to be from a set
        # of given options, so no injection is possible (I think). The `current_status`
        # subquery also has no user input. So I think this should be safe.
    )

    if data_id:
        matching_filter.bindparams(bindparam("data_ids", expanding=True))
    result = await expdb_db.execute(
        matching_filter,
        parameters=parameters,
    )
    rows = result.all()
    datasets: dict[int, dict[str, Any]] = {
        row.did: dict(zip(columns, row, strict=True)) for row in rows
    }
    if not datasets:
        msg = "No datasets match the search criteria."
        raise NoResultsError(msg)

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
    qualities_by_dataset = await database.qualities.get_for_datasets(
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


async def _get_processing_information(
    dataset_id: int,
    connection: AsyncConnection,
) -> ProcessingInformation:
    """Return processing information, if any. Otherwise, all fields `None`."""
    if not (
        data_processed := await database.datasets.get_latest_processing_update(
            dataset_id,
            connection,
        )
    ):
        return ProcessingInformation(date=None, warning=None, error=None)

    date_processed = data_processed.processing_date
    warning = data_processed.warning.strip() if data_processed.warning else None
    error = data_processed.error.strip() if data_processed.error else None
    return ProcessingInformation(date=date_processed, warning=warning, error=error)


async def _get_dataset_raise_otherwise(
    dataset_id: int,
    user: User | None,
    expdb: AsyncConnection,
) -> Row[Any]:
    """Fetch the dataset from the database if it exists and the user has permissions.

    Raises ProblemDetailError if the dataset does not exist or the user can not access it.
    """
    if not (dataset := await database.datasets.get(dataset_id, expdb)):
        msg = f"No dataset with id {dataset_id} found."
        raise DatasetNotFoundError(msg)

    if not await _user_has_access(dataset=dataset, user=user):
        msg = f"No access granted to dataset {dataset_id}."
        raise DatasetNoAccessError(msg)

    return dataset


@router.get("/features/{dataset_id}", response_model_exclude_none=True)
async def get_dataset_features(
    dataset_id: int,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)] = None,
) -> list[Feature]:
    assert expdb is not None  # noqa: S101
    await _get_dataset_raise_otherwise(dataset_id, user, expdb)
    features, ontologies = await asyncio.gather(
        database.datasets.get_features(dataset_id, expdb),
        database.datasets.get_feature_ontologies(dataset_id, expdb),
    )
    for feature in features:
        feature.ontology = ontologies.get(feature.index)

    for feature in [f for f in features if f.data_type == FeatureType.NOMINAL]:
        feature.nominal_values = await database.datasets.get_feature_values(
            dataset_id,
            feature_index=feature.index,
            connection=expdb,
        )

    if not features:
        processing_state = await database.datasets.get_latest_processing_update(dataset_id, expdb)
        if processing_state is None:
            msg = (
                f"Dataset {dataset_id} not processed yet, so features are not yet available. "
                "Please wait for a few minutes."
            )
            raise DatasetNotProcessedError(msg)
        if processing_state.error:
            msg = f"No features found. Additionally, dataset {dataset_id} processed with error."
            raise DatasetProcessingError(msg)
        msg = (
            "No features found. "
            f"Dataset {dataset_id} did not contain any features, or we could not extract them."
        )
        raise DatasetNoFeaturesError(msg)
    return features


@router.post(
    path="/status/update",
)
async def update_dataset_status(
    dataset_id: Annotated[int, Body()],
    status: Annotated[Literal[DatasetStatus.ACTIVE, DatasetStatus.DEACTIVATED], Body()],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> dict[str, str | int]:
    dataset = await _get_dataset_raise_otherwise(dataset_id, user, expdb)

    can_deactivate = dataset.uploader == user.user_id or await user.is_admin()
    if status == DatasetStatus.DEACTIVATED and not can_deactivate:
        msg = f"Dataset {dataset_id} is not owned by you."
        raise DatasetNotOwnedError(msg)

    if status == DatasetStatus.ACTIVE and not await user.is_admin():
        msg = "Only administrators can activate datasets."
        raise DatasetAdminOnlyError(msg)

    current_status = await database.datasets.get_status(dataset_id, expdb)
    if current_status and current_status.status == status:
        msg = f"Illegal status transition, requested status {status} matches current status."
        raise DatasetStatusTransitionError(msg)

    # If current status is unknown, it is effectively "in preparation",
    # So the following transitions are allowed (first 3 transitions are first clause)
    #  - in preparation => active  (add a row)
    #  - in preparation => deactivated  (add a row)
    #  - active => deactivated  (add a row)
    #  - deactivated => active  (delete a row)
    if current_status is None or status == DatasetStatus.DEACTIVATED:
        await database.datasets.update_status(
            dataset_id,
            status,
            user_id=user.user_id,
            connection=expdb,
        )
    elif current_status.status == DatasetStatus.DEACTIVATED:
        await database.datasets.remove_deactivated_status(dataset_id, expdb)
    else:
        msg = f"Unknown status transition: {current_status} -> {status}"
        raise InternalError(msg)

    logger.info(
        "Dataset {dataset_id} changed from {previous} to {current}",
        dataset_id=dataset_id,
        previous=current_status.status if current_status else DatasetStatus.IN_PREPARATION,
        current=status,
    )
    return {"dataset_id": dataset_id, "status": status}


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
async def get_dataset(
    dataset_id: int,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    user_db: Annotated[AsyncConnection, Depends(userdb_connection)] = None,
    expdb_db: Annotated[AsyncConnection, Depends(expdb_connection)] = None,
) -> DatasetMetadata:
    assert user_db is not None  # noqa: S101
    assert expdb_db is not None  # noqa: S101
    dataset = await _get_dataset_raise_otherwise(dataset_id, user, expdb_db)
    if not (
        dataset_file := await database.datasets.get_file(
            file_id=dataset.file_id,
            connection=user_db,
        )
    ):
        msg = f"No data file found for dataset {dataset_id}."
        raise DatasetNoDataFileError(msg)

    tags, description, processing_result, status = await asyncio.gather(
        database.datasets.get_tags_for(dataset_id, expdb_db),
        database.datasets.get_description(dataset_id, expdb_db),
        _get_processing_information(dataset_id, expdb_db),
        database.datasets.get_status(dataset_id, expdb_db),
    )

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
