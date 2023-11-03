""" Translation from https://github.com/openml/OpenML/blob/c19c9b99568c0fabb001e639ff6724b9a754bbc9/openml_OS/models/api/v1/Api_data.php#L707"""
from typing import Any

from sqlalchemy import Engine, text

from database.meta import get_column_names
from database.setup import expdb_database, user_database

_expdb = expdb_database()
_openml = user_database()


def get_dataset(dataset_id: int, engine: Engine = _expdb) -> dict[str, Any] | None:
    columns = get_column_names(engine, "dataset")
    with engine.connect() as conn:
        row = conn.execute(
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


def get_file(file_id: int, engine: Engine = _openml) -> dict[str, Any] | None:
    columns = get_column_names(engine, "file")
    with engine.connect() as conn:
        row = conn.execute(
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


def get_tags(dataset_id: int, engine: Engine = _expdb) -> list[str]:
    columns = get_column_names(engine, "dataset_tag")
    with engine.connect() as conn:
        rows = conn.execute(
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


def get_latest_dataset_description(
    dataset_id: int,
    engine: Engine = _expdb,
) -> dict[str, Any] | None:
    columns = get_column_names(engine, "dataset_description")
    with engine.connect() as conn:
        row = conn.execute(
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


def get_latest_status_update(dataset_id: int, engine: Engine = _expdb) -> dict[str, Any] | None:
    columns = get_column_names(engine, "dataset_status")
    with engine.connect() as conn:
        row = conn.execute(
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


def get_latest_processing_update(dataset_id: int, engine: Engine = _expdb) -> dict[str, Any] | None:
    columns = get_column_names(engine, "data_processed")
    with engine.connect() as conn:
        row = conn.execute(
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
