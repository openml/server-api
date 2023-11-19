"""
We add separate endpoints for old-style JSON responses, so they don't clutter the schema of the
new API, and are easily removed later.
"""
import http.client
from enum import StrEnum
from typing import Annotated, Any, Literal

from database.datasets import get_tags
from database.datasets import tag_dataset as db_tag_dataset
from database.users import APIKey, User, UserGroup
from fastapi import APIRouter, Body, Depends, HTTPException
from schemas.datasets.openml import DatasetStatus
from sqlalchemy import Connection

from routers.dependencies import Pagination, expdb_connection, fetch_user, userdb_connection
from routers.types import CasualString128, SystemString64
from routers.v2.datasets import get_dataset

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])


@router.post(
    path="/tag",
)
def tag_dataset(
    data_id: Annotated[int, Body()],
    tag: SystemString64,
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
    data_version: Annotated[int | None, Body()] = None,
    status: Annotated[DatasetStatusFilter, Body()] = DatasetStatusFilter.ACTIVE,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb_db: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[Literal["data"], dict[Literal["dataset"], list[dict[str, Any]]]]:
    # $legal_filters = array('tag', 'data_id',
    # 'data_version', 'uploader', 'number_instances', 'number_features', 'number_classes',
    # 'number_missing_values');
    from sqlalchemy import text

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
    where_name = "" if data_name is None else f"AND `name`='{data_name}'"
    where_version = "" if data_version is None else f"AND `version`={data_version}"
    matching_status = text(
        f"""
        SELECT d.`did`,d.`name`,d.`version`,d.`format`,d.`file_id`,
               IFNULL(cs.`status`, 'in_preparation')
        FROM dataset AS d
        LEFT JOIN ({current_status}) AS cs ON d.`did`=cs.`did`
        WHERE {visible_to_user} {where_name} {where_version}
        AND IFNULL(cs.`status`, 'in_preparation') IN ({where_status})
        LIMIT {pagination.limit} OFFSET {pagination.offset}
        """,  # nosec
        # I am not sure how to do this correctly without an error from Bandit here.
        # However, the `status` input is already checked by FastAPI to be from a set
        # of given options, so no injection is possible (I think). The `current_status`
        # subquery also has no user input. So I think this should be safe.
    )
    columns = ["did", "name", "version", "format", "file_id", "status"]
    rows = expdb_db.execute(matching_status)
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
    qualities_filter = ",".join(f"'{q}'" for q in qualities_to_show)
    dids = ",".join(str(did) for did in datasets)
    qualities = text(
        f"""
        SELECT `data`, `quality`, `value`
        FROM data_quality
        WHERE `data` in ({dids}) AND `quality` IN ({qualities_filter})
        """,  # nosec  - similar to above, no user input
    )
    qualities = expdb_db.execute(qualities)
    for did, quality, value in qualities:
        datasets[did]["quality"].append({"name": quality, "value": value})
    return {"data": {"dataset": list(datasets.values())}}


@router.get(
    path="/{dataset_id}",
    description="Get old-style wrapped meta-data for dataset with ID `dataset_id`.",
)
def get_dataset_wrapped(
    dataset_id: int,
    api_key: APIKey | None = None,
    user_db: Annotated[Connection, Depends(userdb_connection)] = None,
    expdb_db: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[str, dict[str, Any]]:
    try:
        dataset = get_dataset(
            user_db=user_db,
            expdb_db=expdb_db,
            dataset_id=dataset_id,
            api_key=api_key,
        ).model_dump(by_alias=True)
    except HTTPException as e:
        raise HTTPException(
            status_code=http.client.PRECONDITION_FAILED,
            detail=e.detail,
        ) from None
    if processing_data := dataset.get("processing_date"):
        dataset["processing_date"] = str(processing_data).replace("T", " ")
    if parquet_url := dataset.get("parquet_url"):
        dataset["parquet_url"] = str(parquet_url).replace("https", "http")
    if minio_url := dataset.get("minio_url"):
        dataset["minio_url"] = str(minio_url).replace("https", "http")

    manual = []
    # ref test.openml.org/d/33 (contributor) and d/34 (creator)
    #   contributor/creator in database is '""'
    #   json content is []
    for field in ["contributor", "creator"]:
        if dataset[field] == [""]:
            dataset[field] = []
            manual.append(field)

    if isinstance(dataset["original_data_url"], list):
        dataset["original_data_url"] = ", ".join(str(url) for url in dataset["original_data_url"])

    for field, value in list(dataset.items()):
        if field in manual:
            continue
        if isinstance(value, int):
            dataset[field] = str(value)
        elif isinstance(value, list) and len(value) == 1:
            dataset[field] = str(value[0])
        if not dataset[field]:
            del dataset[field]

    if "description" not in dataset:
        dataset["description"] = []

    return {"data_set_description": dataset}
