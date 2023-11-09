"""
We add separate endpoints for old-style JSON responses, so they don't clutter the schema of the
new API, and are easily removed later.
"""
import http.client
from typing import Annotated, Any

from database.datasets import get_tags
from database.datasets import tag_dataset as db_tag_dataset
from database.users import APIKey, User
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import Connection

from routers.dependencies import expdb_connection, fetch_user, userdb_connection
from routers.types import SystemString64
from routers.v2.datasets import get_dataset

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])


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
