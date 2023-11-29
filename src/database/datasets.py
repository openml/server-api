""" Translation from https://github.com/openml/OpenML/blob/c19c9b99568c0fabb001e639ff6724b9a754bbc9/openml_OS/models/api/v1/Api_data.php#L707"""
from collections import defaultdict
from typing import Any, Iterable

from schemas.datasets.openml import Quality
from sqlalchemy import Connection, text

from database.meta import get_column_names


def get_qualities_for_dataset(dataset_id: int, connection: Connection) -> list[Quality]:
    rows = connection.execute(
        text(
            """
        SELECT `quality`,`value`
        FROM data_quality
        WHERE `data`=:dataset_id
        """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    return [Quality(name=row.quality, value=row.value) for row in rows]


def get_qualities_for_datasets(
    dataset_ids: Iterable[int],
    qualities: Iterable[str],
    connection: Connection,
) -> dict[int, list[Quality]]:
    qualities_filter = ",".join(f"'{q}'" for q in qualities)
    dids = ",".join(str(did) for did in dataset_ids)
    qualities_query = text(
        f"""
        SELECT `data`, `quality`, `value`
        FROM data_quality
        WHERE `data` in ({dids}) AND `quality` IN ({qualities_filter})
        """,  # nosec  - similar to above, no user input
    )
    rows = connection.execute(qualities_query)
    qualities_by_id = defaultdict(list)
    for did, quality, value in rows:
        if value is not None:
            qualities_by_id[did].append(Quality(name=quality, value=value))
    return dict(qualities_by_id)


def list_all_qualities(connection: Connection) -> list[str]:
    # The current implementation only fetches *used* qualities, otherwise you should
    # query: SELECT `name` FROM `quality` WHERE `type`='DataQuality'
    qualities = connection.execute(
        text(
            """
        SELECT DISTINCT(`quality`)
        FROM data_quality
        """,
        ),
    )
    return [quality.quality for quality in qualities]


def get_dataset(dataset_id: int, connection: Connection) -> dict[str, Any] | None:
    columns = get_column_names(connection, "dataset")
    row = connection.execute(
        text(
            """
    SELECT *
    FROM dataset
    WHERE did = :dataset_id
    """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    return dict(zip(columns, result[0], strict=True)) if (result := list(row)) else None


def get_file(file_id: int, connection: Connection) -> dict[str, Any] | None:
    columns = get_column_names(connection, "file")
    row = connection.execute(
        text(
            """
    SELECT *
    FROM file
    WHERE id = :file_id
    """,
        ),
        parameters={"file_id": file_id},
    )
    return dict(zip(columns, result[0], strict=True)) if (result := list(row)) else None


def get_tags(dataset_id: int, connection: Connection) -> list[str]:
    columns = get_column_names(connection, "dataset_tag")
    rows = connection.execute(
        text(
            """
    SELECT *
    FROM dataset_tag
    WHERE id = :dataset_id
    """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    return [dict(zip(columns, row, strict=True))["tag"] for row in rows]


def tag_dataset(user_id: int, dataset_id: int, tag: str, connection: Connection) -> None:
    connection.execute(
        text(
            """
    INSERT INTO dataset_tag(`id`, `tag`, `uploader`)
    VALUES (:dataset_id, :tag, :user_id)
    """,
        ),
        parameters={
            "dataset_id": dataset_id,
            "user_id": user_id,
            "tag": tag,
        },
    )


def get_latest_dataset_description(
    dataset_id: int,
    connection: Connection,
) -> dict[str, Any] | None:
    columns = get_column_names(connection, "dataset_description")
    row = connection.execute(
        text(
            """
    SELECT *
    FROM dataset_description
    WHERE did = :dataset_id
    ORDER BY version DESC
    """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    return dict(zip(columns, result[0], strict=True)) if (result := list(row)) else None


def get_latest_status_update(dataset_id: int, connection: Connection) -> dict[str, Any] | None:
    columns = get_column_names(connection, "dataset_status")
    row = connection.execute(
        text(
            """
    SELECT *
    FROM dataset_status
    WHERE did = :dataset_id
    ORDER BY status_date DESC
    """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    return (
        dict(zip(columns, result[0], strict=True), strict=True) if (result := list(row)) else None
    )


def get_latest_processing_update(dataset_id: int, connection: Connection) -> dict[str, Any] | None:
    columns = get_column_names(connection, "data_processed")
    row = connection.execute(
        text(
            """
    SELECT *
    FROM data_processed
    WHERE did = :dataset_id
    ORDER BY processing_date DESC
    """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    return (
        dict(zip(columns, result[0], strict=True), strict=True) if (result := list(row)) else None
    )
