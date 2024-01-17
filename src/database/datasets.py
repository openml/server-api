""" Translation from https://github.com/openml/OpenML/blob/c19c9b99568c0fabb001e639ff6724b9a754bbc9/openml_OS/models/api/v1/Api_data.php#L707"""
import datetime
from collections import defaultdict
from typing import Iterable

from schemas.datasets.openml import Feature, Quality
from sqlalchemy import Connection, text
from sqlalchemy.engine import Row


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


def _get_qualities_for_datasets(
    dataset_ids: Iterable[int],
    qualities: Iterable[str],
    connection: Connection,
) -> dict[int, list[Quality]]:
    """Don't call with user-provided input, as query is not parameterized."""
    qualities_filter = ",".join(f"'{q}'" for q in qualities)
    dids = ",".join(str(did) for did in dataset_ids)
    qualities_query = text(
        f"""
        SELECT `data`, `quality`, `value`
        FROM data_quality
        WHERE `data` in ({dids}) AND `quality` IN ({qualities_filter})
        """,  # nosec  - dids and qualities are not user-provided
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


def get_dataset(dataset_id: int, connection: Connection) -> Row | None:
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
    return row.one_or_none()


def get_file(file_id: int, connection: Connection) -> Row | None:
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
    return row.one_or_none()


def get_tags(dataset_id: int, connection: Connection) -> list[str]:
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
    return [row.tag for row in rows]


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
) -> Row | None:
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
    return row.first()


def get_latest_status_update(dataset_id: int, connection: Connection) -> Row | None:
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
    return row.first()


def get_latest_processing_update(dataset_id: int, connection: Connection) -> Row | None:
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
    return row.one_or_none()


def get_features_for_dataset(dataset_id: int, connection: Connection) -> list[Feature]:
    rows = connection.execute(
        text(
            """
            SELECT `index`,`name`,`data_type`,`is_target`,
            `is_row_identifier`,`is_ignore`,`NumberOfMissingValues` as `number_of_missing_values`
            FROM data_feature
            WHERE `did` = :dataset_id
            """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    return [Feature(**row, nominal_values=None) for row in rows.mappings()]


def get_feature_values(dataset_id: int, feature_index: int, connection: Connection) -> list[str]:
    rows = connection.execute(
        text(
            """
            SELECT `value`
            FROM data_feature_value
            WHERE `did` = :dataset_id AND `index` = :feature_index
            """,
        ),
        parameters={"dataset_id": dataset_id, "feature_index": feature_index},
    )
    return [row.value for row in rows]


def insert_status_for_dataset(
    dataset_id: int,
    user_id: int,
    status: str,
    connection: Connection,
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO dataset_status(`did`,`status`,`status_date`,`user_id`)
            VALUES (:dataset, :status, :date, :user)
            """,
        ),
        parameters={
            "dataset": dataset_id,
            "status": status,
            "date": datetime.datetime.now(),
            "user": user_id,
        },
    )


def remove_deactivated_status(dataset_id: int, connection: Connection) -> None:
    connection.execute(
        text(
            """
            DELETE FROM dataset_status
            WHERE `did` = :data AND `status`='deactivated'
            """,
        ),
        parameters={"data": dataset_id},
    )
