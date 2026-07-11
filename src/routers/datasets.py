"""Defines endpoints relating to Datasets.

A dataset includes both the "data", e.g., the table or parquet file, as well as its metadata.
The metadata is partially provided by the user (for example, the name or description),
'features' that are partially parsed from the data file (for example, column names),
and 'qualities' (or meta-features) that describe the data (for example, number of rows or columns).
"""

import html
import re
from datetime import datetime
from enum import StrEnum
from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated, Any, Literal, NamedTuple

from fastapi import APIRouter, Body, Depends, Path, Query
from loguru import logger
from sqlalchemy import bindparam, text

import database.datasets
import database.qualities
from config import get_config
from core.access import user_has_access
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
    TagNotFoundError,
    TagNotOwnedError,
)
from core.formatting import csv_as_list
from core.types import (
    CasualString128,
    Identifier,
    IntegerRange,
    TagString,
    integer_range_regex,
)
from database.exceptions import DuplicatePrimaryKeyError, ForeignKeyConstraintError
from database.models.base import UntypedRow
from database.users import User
from routers.dependencies import (
    Pagination,
    expdb_session,
    fetch_user,
    fetch_user_or_raise,
    userdb_session,
)
from routers.schemas.core import TagInfo
from routers.schemas.datasets import (
    DatasetFileFormat,
    DatasetMetadata,
    DatasetStatus,
    Feature,
    FeatureType,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Row
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _format_parquet_url(dataset: UntypedRow) -> str | None:
    if dataset.format.lower() != DatasetFileFormat.ARFF:
        return None

    minio_base_url = get_config().routing.minio_url
    ten_thousands_prefix = f"{dataset.did // 10_000:04d}"
    padded_id = f"{dataset.did:04d}"
    return f"{minio_base_url}datasets/{ten_thousands_prefix}/{padded_id}/dataset_{dataset.did}.pq"


def _format_dataset_url(dataset: UntypedRow) -> str:
    base_url = get_config().routing.server_url
    filename = f"{html.escape(dataset.name)}.{dataset.format.lower()}"
    return f"{base_url}data/v1/download/{dataset.file_id}/{filename}"


@router.post(
    path="/tag",
    deprecated=True,
)
async def tag_dataset(
    data_id: Annotated[Identifier, Body()],
    tag: Annotated[TagString, Body()],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb: Annotated[AsyncSession, Depends(expdb_session)],
) -> dict[str, dict[str, Any]]:
    """Add a tag to the dataset, this tag is publicly visible to all users."""
    await tag_dataset_new(data_id, tag, user, expdb)

    tags = await database.datasets.get_tags_for(data_id, expdb)

    return {
        "data_tag": {"id": str(data_id), "tag": tags},
    }


@router.post(
    path="/{identifier}/tags",
)
async def tag_dataset_new(
    identifier: Annotated[Identifier, Path()],
    tag: Annotated[TagString, Body(embed=True)],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb: Annotated[AsyncSession, Depends(expdb_session)],
) -> None:
    """Add a tag to the dataset, this tag is publicly visible to all users."""
    try:
        await database.datasets.tag(identifier, tag, user_id=user.user_id, session=expdb)
    except ForeignKeyConstraintError:
        msg = f"Dataset {identifier} not found."
        raise DatasetNotFoundError(msg, code=472) from None
    except DuplicatePrimaryKeyError:
        msg = f"Dataset {identifier} already tagged with {tag!r}."
        raise TagAlreadyExistsError(msg) from None

    logger.info("Dataset {identifier} tagged '{tag}'.", identifier=identifier, tag=tag)


@router.post(path="/untag", deprecated=True)
async def untag_dataset_like_php(
    data_id: Annotated[Identifier, Body()],
    tag: Annotated[TagString, Body()],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb_db: Annotated[AsyncSession, Depends(expdb_session)],
) -> dict[Literal["data_untag"], TagInfo]:
    """Remove a tag from the dataset with a response similar to the old PHP server."""
    await untag_dataset(data_id, tag, user, expdb_db)
    tags = await database.datasets.get_tags_for(dataset_id=data_id, session=expdb_db)
    tag_info: TagInfo = {"id": str(data_id)}
    if len(tags) == 1:
        tag_info["tag"] = tags[0]
    elif tags:
        tag_info["tag"] = tags
    return {"data_untag": tag_info}


@router.delete(path="/{identifier}/tag", status_code=HTTPStatus.NO_CONTENT)
async def untag_dataset(
    identifier: Identifier,
    tag: Annotated[TagString, Query()],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb_db: Annotated[AsyncSession, Depends(expdb_session)],
) -> None:
    """Remove a tag that you added to a dataset, or from a dataset you uploaded."""
    dataset_tag = await database.datasets.get_tag(identifier, tag, expdb_db)
    if not dataset_tag:
        try:
            await _get_dataset_raise_otherwise(identifier, user, expdb_db)
        except DatasetNotFoundError, DatasetNoAccessError:
            msg = f"Cannot remove {tag!r}, because dataset {identifier} is not found."
            raise DatasetNotFoundError(msg, code=472) from None
        msg = f"Tag {tag!r} for dataset {identifier} not found."
        raise TagNotFoundError(msg)
    if dataset_tag.uploader != user.user_id and not (await user.is_admin()):
        msg = f"You are not allowed to remove {tag!r} from dataset {identifier}."
        raise TagNotOwnedError(msg)
    await database.datasets.delete_tag(identifier, tag, expdb_db)


class DatasetStatusFilter(StrEnum):
    """Legal filter values for the Dataset Status filter."""

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
    expdb_db: Annotated[AsyncSession, Depends(expdb_session)],
    pagination: Annotated[Pagination, Body(default_factory=Pagination)],
    data_name: Annotated[CasualString128 | None, Body()] = None,
    tag: Annotated[TagString | None, Body()] = None,
    data_version: Annotated[
        Identifier | None,
        Body(description="The dataset version to include in the search."),
    ] = None,
    uploader: Annotated[
        Identifier | None,
        Body(description="User id of the uploader whose datasets to include in the search."),
    ] = None,
    data_id: Annotated[
        list[Identifier] | None,
        Body(
            description="The dataset(s) to include in the search. "
            "If none are specified, all datasets are included.",
        ),
    ] = None,
    number_instances: Annotated[IntegerRange | None, Body()] = None,
    number_features: Annotated[IntegerRange | None, Body()] = None,
    number_classes: Annotated[IntegerRange | None, Body()] = None,
    number_missing_values: Annotated[IntegerRange | None, Body()] = None,
    status: Annotated[DatasetStatusFilter, Body()] = DatasetStatusFilter.ACTIVE,
    user: Annotated[User | None, Depends(fetch_user)] = None,
) -> list[dict[str, Any]]:
    """List all datasets that match the filters."""
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
        params=parameters,
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
        session=expdb_db,
    )
    for did, qualities in qualities_by_dataset.items():
        datasets[did]["quality"] = qualities
    return list(datasets.values())


class ProcessingInformation(NamedTuple):
    """Metadata about an attempt to process a dataset."""

    date: datetime | None
    warning: str | None
    error: str | None


async def _get_processing_information(
    dataset_id: Identifier,
    session: AsyncSession,
) -> ProcessingInformation:
    """Return processing information, if any. Otherwise, all fields `None`."""
    if not (
        data_processed := await database.datasets.get_latest_processing_update(
            dataset_id,
            session,
        )
    ):
        return ProcessingInformation(date=None, warning=None, error=None)

    date_processed = data_processed.processing_date
    warning = data_processed.warning.strip() if data_processed.warning else None
    error = data_processed.error.strip() if data_processed.error else None
    return ProcessingInformation(date=date_processed, warning=warning, error=error)


async def _get_dataset_raise_otherwise(
    dataset_id: Identifier,
    user: User | None,
    expdb: AsyncSession,
) -> Row[Any]:
    """Fetch the dataset from the database if it exists and the user has permissions.

    Raises ProblemDetailError if the dataset does not exist or the user can not access it.
    """
    if not (dataset := await database.datasets.get(dataset_id, expdb)):
        msg = f"No dataset with id {dataset_id} found."
        raise DatasetNotFoundError(msg)

    if not await user_has_access(dataset=dataset, user=user):
        msg = f"No access granted to dataset {dataset_id}."
        raise DatasetNoAccessError(msg)

    return dataset


@router.get("/features/{dataset_id}", response_model_exclude_none=True)
async def get_dataset_features(
    dataset_id: Identifier,
    expdb: Annotated[AsyncSession, Depends(expdb_session)],
    user: Annotated[User | None, Depends(fetch_user)] = None,
) -> list[Feature]:
    """Return metadata for each feature (column) in the dataset."""
    assert expdb is not None  # noqa: S101
    await _get_dataset_raise_otherwise(dataset_id, user, expdb)
    features = await database.datasets.get_features(dataset_id, expdb)
    ontologies = await database.datasets.get_feature_ontologies(dataset_id, expdb)
    for feature in features:
        feature.ontology = ontologies.get(feature.index)

    for feature in [f for f in features if f.data_type == FeatureType.NOMINAL]:
        feature.nominal_values = await database.datasets.get_feature_values(
            dataset_id,
            feature_index=feature.index,
            session=expdb,
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
    dataset_id: Annotated[Identifier, Body()],
    status: Annotated[Literal[DatasetStatus.ACTIVE, DatasetStatus.DEACTIVATED], Body()],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb: Annotated[AsyncSession, Depends(expdb_session)],
) -> dict[str, str | int]:
    """Update the status of the dataset. Can be used to deactivate a dataset."""
    dataset = await _get_dataset_raise_otherwise(dataset_id, user, expdb)

    can_deactivate = dataset.uploader == user.user_id or await user.is_admin()
    if status == DatasetStatus.DEACTIVATED and not can_deactivate:
        msg = f"Dataset {dataset_id} is not owned by you."
        raise DatasetNotOwnedError(msg)

    if status == DatasetStatus.ACTIVE and not await user.is_admin():
        msg = "Only administrators can activate datasets."
        raise DatasetAdminOnlyError(msg)

    current_status = await database.datasets.get_status(dataset_id, expdb)
    if current_status == status:
        msg = f"Illegal status transition, requested status {status} matches current status."
        raise DatasetStatusTransitionError(msg)

    # If current status is unknown, it is effectively "in preparation",
    # So the following transitions are allowed (first 3 transitions are first clause)
    #  - in preparation => active  (add a row)
    #  - in preparation => deactivated  (add a row)
    #  - active => deactivated  (add a row)
    #  - deactivated => active  (delete a row)
    if current_status == DatasetStatus.IN_PREPARATION or status == DatasetStatus.DEACTIVATED:
        await database.datasets.update_status(
            dataset_id,
            status,
            user_id=user.user_id,
            session=expdb,
        )
    elif current_status == DatasetStatus.DEACTIVATED:
        await database.datasets.remove_deactivated_status(dataset_id, expdb)
    else:
        msg = f"Unknown status transition: {current_status} -> {status}"
        raise InternalError(msg)

    logger.info(
        "Dataset {dataset_id} changed from {previous} to {current}",
        dataset_id=dataset_id,
        previous=current_status,
        current=status,
    )
    return {"dataset_id": dataset_id, "status": status}


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
async def get_dataset(
    dataset_id: Identifier,
    userdb_session: Annotated[AsyncSession, Depends(userdb_session)],
    expdb_session: Annotated[AsyncSession, Depends(expdb_session)],
    user: Annotated[User | None, Depends(fetch_user)] = None,
) -> DatasetMetadata:
    """Get the user-provided metadata for a dataset."""
    dataset = await _get_dataset_raise_otherwise(dataset_id, user, expdb_session)
    if not (
        dataset_file := await database.datasets.get_file(
            file_id=dataset.file_id,
            session=userdb_session,
        )
    ):
        msg = f"No data file found for dataset {dataset_id}."
        raise DatasetNoDataFileError(msg)

    tags = await database.datasets.get_tags_for(dataset_id, expdb_session)
    description = await database.datasets.get_description(dataset_id, expdb_session)
    processing_result = await _get_processing_information(dataset_id, expdb_session)
    status = await database.datasets.get_status(dataset_id, expdb_session)

    description_ = ""
    if description:
        description_ = description.description.replace("\r", "").strip()

    dataset_url = _format_dataset_url(dataset)
    parquet_url = _format_parquet_url(dataset)

    contributors = csv_as_list(dataset.contributor, unquote_items=True)
    creators = csv_as_list(dataset.creator, unquote_items=True)
    ignore_attribute = csv_as_list(dataset.ignore_attribute, unquote_items=True)
    row_id_attribute = csv_as_list(dataset.row_id_attribute, unquote_items=True)
    original_data_url = csv_as_list(dataset.original_data_url, unquote_items=True)
    default_target_attribute = csv_as_list(dataset.default_target_attribute, unquote_items=True)

    return DatasetMetadata(
        id=dataset.did,
        visibility=dataset.visibility,
        status=status,
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
