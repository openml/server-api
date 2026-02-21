"""Translation from https://github.com/openml/OpenML/blob/c19c9b99568c0fabb001e639ff6724b9a754bbc9/openml_OS/models/api/v1/Api_data.php#L707"""

import datetime

from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncConnection

from schemas.datasets.openml import Feature


async def get(id_: int, connection: AsyncConnection) -> Row | None:
    row = await connection.execute(
        text(
            """
    SELECT *
    FROM dataset
    WHERE did = :dataset_id
    """,
        ),
        parameters={"dataset_id": id_},
    )
    return row.one_or_none()


async def get_file(*, file_id: int, connection: AsyncConnection) -> Row | None:
    row = await connection.execute(
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


async def get_tags_for(id_: int, connection: AsyncConnection) -> list[str]:
    rows = await connection.execute(
        text(
            """
    SELECT *
    FROM dataset_tag
    WHERE id = :dataset_id
    """,
        ),
        parameters={"dataset_id": id_},
    )
    return [row.tag for row in rows]


async def tag(id_: int, tag_: str, *, user_id: int, connection: AsyncConnection) -> None:
    await connection.execute(
        text(
            """
    INSERT INTO dataset_tag(`id`, `tag`, `uploader`)
    VALUES (:dataset_id, :tag, :user_id)
    """,
        ),
        parameters={
            "dataset_id": id_,
            "user_id": user_id,
            "tag": tag_,
        },
    )


async def get_description(
    id_: int,
    connection: AsyncConnection,
) -> Row | None:
    """Get the most recent description for the dataset."""
    row = await connection.execute(
        text(
            """
    SELECT *
    FROM dataset_description
    WHERE did = :dataset_id
    ORDER BY version DESC
    """,
        ),
        parameters={"dataset_id": id_},
    )
    return row.first()


async def get_status(id_: int, connection: AsyncConnection) -> Row | None:
    """Get most recent status for the dataset."""
    row = await connection.execute(
        text(
            """
    SELECT *
    FROM dataset_status
    WHERE did = :dataset_id
    ORDER BY status_date DESC
    """,
        ),
        parameters={"dataset_id": id_},
    )
    return row.first()


async def get_latest_processing_update(dataset_id: int, connection: AsyncConnection) -> Row | None:
    row = await connection.execute(
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


async def get_features(dataset_id: int, connection: AsyncConnection) -> list[Feature]:
    rows = await connection.execute(
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


async def get_feature_values(
    dataset_id: int,
    *,
    feature_index: int,
    connection: AsyncConnection,
) -> list[str]:
    rows = await connection.execute(
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


async def update_status(
    dataset_id: int,
    status: str,
    *,
    user_id: int,
    connection: AsyncConnection,
) -> None:
    await connection.execute(
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


async def remove_deactivated_status(dataset_id: int, connection: AsyncConnection) -> None:
    await connection.execute(
        text(
            """
            DELETE FROM dataset_status
            WHERE `did` = :data AND `status`='deactivated'
            """,
        ),
        parameters={"data": dataset_id},
    )
