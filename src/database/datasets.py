"""Translation from https://github.com/openml/OpenML/blob/c19c9b99568c0fabb001e639ff6724b9a754bbc9/openml_OS/models/api/v1/Api_data.php#L707."""

import datetime
from collections import defaultdict
from typing import TYPE_CHECKING, Literal

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from core.types import Identifier, TagString
from database.exceptions import (
    _DUPLICATE_ENTRY,
    _FOREIGN_KEY_CONSTRAINT_FAILED,
    DuplicatePrimaryKeyError,
    ForeignKeyConstraintError,
)
from database.models.base import UntypedRow
from routers.schemas.datasets import DatasetStatus, Feature

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get(dataset_id: Identifier, session: AsyncSession) -> UntypedRow | None:
    row = await session.execute(
        text(
            """
    SELECT *
    FROM dataset
    WHERE did = :dataset_id
    """,
        ),
        params={"dataset_id": dataset_id},
    )
    return row.one_or_none()


async def get_file(*, file_id: Identifier, session: AsyncSession) -> UntypedRow | None:
    row = await session.execute(
        text(
            """
    SELECT *
    FROM file
    WHERE id = :file_id
    """,
        ),
        params={"file_id": file_id},
    )
    return row.one_or_none()


async def get_tag(
    dataset_id: Identifier,
    tag: TagString,
    session: AsyncSession,
) -> UntypedRow | None:
    return (
        await session.execute(
            text(
                """
    SELECT *
    FROM dataset_tag
    WHERE id = :dataset_id AND tag = :tag
    """,
            ),
            params={"dataset_id": dataset_id, "tag": tag},
        )
    ).first()


async def delete_tag(dataset_id: Identifier, tag: TagString, session: AsyncSession) -> None:
    await session.execute(
        text(
            """
    DELETE FROM dataset_tag
    WHERE id = :dataset_id AND tag = :tag
    """,
        ),
        params={"dataset_id": dataset_id, "tag": tag},
    )


async def get_tags_for(dataset_id: Identifier, session: AsyncSession) -> list[str]:
    row = await session.execute(
        text(
            """
    SELECT *
    FROM dataset_tag
    WHERE id = :dataset_id
    """,
        ),
        params={"dataset_id": dataset_id},
    )
    rows = row.all()
    return [row.tag for row in rows]


async def tag(
    dataset_id: Identifier,
    tag: str,
    *,
    user_id: Identifier,
    session: AsyncSession,
) -> None:
    try:
        await session.execute(
            text(
                """
        INSERT INTO dataset_tag(`id`, `tag`, `uploader`)
        VALUES (:dataset_id, :tag, :user_id)
        """,
            ),
            params={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "tag": tag,
            },
        )
    except IntegrityError as e:
        if e.orig is None:
            raise
        code, msg = e.orig.args
        if code == _FOREIGN_KEY_CONSTRAINT_FAILED:
            raise ForeignKeyConstraintError(msg) from e
        if code == _DUPLICATE_ENTRY:
            raise DuplicatePrimaryKeyError(msg) from e
        raise


async def get_description(
    dataset_id: Identifier,
    session: AsyncSession,
) -> UntypedRow | None:
    """Get the most recent description for the dataset."""
    row = await session.execute(
        text(
            """
    SELECT *
    FROM dataset_description
    WHERE did = :dataset_id
    ORDER BY version DESC
    """,
        ),
        params={"dataset_id": dataset_id},
    )
    return row.first()


async def get_status(dataset_id: Identifier, session: AsyncSession) -> DatasetStatus:
    """Get most recent status for the dataset."""
    row = (
        await session.execute(
            text(
                """
    SELECT status
    FROM dataset_status
    WHERE did = :dataset_id
    ORDER BY status_date DESC
    LIMIT 1
    """,
            ),
            params={"dataset_id": dataset_id},
        )
    ).first()
    return DatasetStatus(row.status) if row else DatasetStatus.IN_PREPARATION


async def get_latest_processing_update(
    dataset_id: Identifier,
    session: AsyncSession,
) -> UntypedRow | None:
    row = await session.execute(
        text(
            """
    SELECT *
    FROM data_processed
    WHERE did = :dataset_id
    ORDER BY processing_date DESC
    """,
        ),
        params={"dataset_id": dataset_id},
    )
    return row.first()


async def get_features(dataset_id: Identifier, session: AsyncSession) -> list[Feature]:
    row = await session.execute(
        text(
            """
            SELECT `index`,`name`,`data_type`,`is_target`,
            `is_row_identifier`,`is_ignore`,`NumberOfMissingValues` as `number_of_missing_values`
            FROM data_feature
            WHERE `did` = :dataset_id
            """,
        ),
        params={"dataset_id": dataset_id},
    )
    rows = row.mappings().all()
    return [Feature(**row, nominal_values=None) for row in rows]


async def get_feature_ontologies(
    dataset_id: Identifier,
    session: AsyncSession,
) -> dict[int, list[str]]:
    rows = await session.execute(
        text(
            """
            SELECT `index`, `value`
            FROM data_feature_description
            WHERE `did` = :dataset_id AND `description_type` = 'ontology'
            """,
        ),
        params={"dataset_id": dataset_id},
    )
    ontologies: dict[int, list[str]] = defaultdict(list)
    for row in rows.mappings():
        ontologies[row["index"]].append(row["value"])
    return ontologies


async def get_feature_values(
    dataset_id: Identifier,
    *,
    feature_index: int,
    session: AsyncSession,
) -> list[str]:
    row = await session.execute(
        text(
            """
            SELECT `value`
            FROM data_feature_value
            WHERE `did` = :dataset_id AND `index` = :feature_index
            """,
        ),
        params={"dataset_id": dataset_id, "feature_index": feature_index},
    )
    rows = row.all()
    return [row.value for row in rows]


async def update_status(
    dataset_id: Identifier,
    status: Literal[DatasetStatus.ACTIVE, DatasetStatus.DEACTIVATED],
    *,
    user_id: Identifier,
    session: AsyncSession,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO dataset_status(`did`,`status`,`status_date`,`user_id`)
            VALUES (:dataset, :status, :date, :user)
            """,
        ),
        params={
            "dataset": dataset_id,
            "status": status,
            "date": datetime.datetime.now(datetime.UTC),
            "user": user_id,
        },
    )


async def remove_deactivated_status(dataset_id: Identifier, session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            DELETE FROM dataset_status
            WHERE `did` = :data AND `status`='deactivated'
            """,
        ),
        params={"data": dataset_id},
    )
