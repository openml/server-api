""" Translation from https://github.com/openml/OpenML/blob/c19c9b99568c0fabb001e639ff6724b9a754bbc9/openml_OS/models/api/v1/Api_data.php#L707"""
import html
from typing import Any

from schemas.datasets.openml import DatasetMetadata, DatasetStatus, Visibility
from sqlalchemy import Engine, create_engine, text

expdb = create_engine(
    "mysql://root:ok@127.0.0.1:3306/openml_expdb",
    echo=True,
    pool_recycle=3600,
)
openml = create_engine(
    "mysql://root:ok@127.0.0.1:3306/openml",
    echo=True,
    pool_recycle=3600,
)


def get_column_names(database: Engine, table: str) -> list[str]:
    with database.connect() as conn:
        result = conn.execute(
            text(
                """
      SELECT column_name
      FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_NAME = :table_name;
      """,
            ),
            parameters={"table_name": table},
        )
    return [colname for colname, in result.all()]


def get_dataset(dataset_id: int) -> dict[str, Any] | None:
    columns = get_column_names(expdb, "dataset")
    with expdb.connect() as conn:
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


def get_file(file_id: int) -> dict[str, Any] | None:
    columns = get_column_names(openml, "file")
    with openml.connect() as conn:
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


def get_tags(dataset_id: int) -> list[dict[str, Any]]:
    columns = get_column_names(expdb, "dataset_tag")
    with expdb.connect() as conn:
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
    return [dict(zip(columns, row, strict=True)) for row in rows]


def get_latest_dataset_description(dataset_id: int) -> dict[str, Any] | None:
    columns = get_column_names(expdb, "dataset_description")
    with expdb.connect() as conn:
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


def get_latest_status_update(dataset_id: int) -> dict[str, Any] | None:
    columns = get_column_names(expdb, "dataset_status")
    with expdb.connect() as conn:
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
        dict(zip(columns, result[0], strict=True), strict=True)
        if (result := list(row))
        else None
    )


def get_latest_processing_update(dataset_id: int) -> dict[str, Any] | None:
    columns = get_column_names(expdb, "data_processed")
    with expdb.connect() as conn:
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
        dict(zip(columns, result[0], strict=True), strict=True)
        if (result := list(row))
        else None
    )


def get_dataset_description(dataset_id: int) -> DatasetMetadata:
    if not isinstance(dataset_id, int):
        # Error Code 110
        msg = f"type(dataset_id)={type(dataset_id)!r} but should be `int`."
        raise TypeError(msg)

    if not (dataset := get_dataset(dataset_id)):
        # Error Code 111
        msg = f"No dataset associated with dataset_id={dataset_id!r}."
        raise ValueError(msg)

    if dataset["visibility"] != Visibility.PUBLIC:
        # if the dataset is private, user must be uploader or admin
        # Error Code 112
        msg = "Access for private datasets not yet ported."
        raise NotImplementedError(msg)

    if not (file := get_file(dataset["file_id"])):
        msg = f"No data file associated with dataset_id={dataset_id!r}."
        raise FileNotFoundError(msg)

    tags = [row["tag"] for row in get_tags(dataset_id)]

    BASE_URL = "https://www.openml.org/"
    filename = f"{html.escape(dataset['name'])}.{dataset['format'].lower()}"
    dataset_url = f"{BASE_URL}/data/v1/download/{dataset['file_id']}/{filename}"

    if dataset["format"] != "Sparse_ARFF":
        minio_base_url = "https://openml1.win.tue.nl/dataset"
        parquet_url = f"{minio_base_url}/{dataset_id}/dataset_{dataset_id}.pq"
    else:
        parquet_url = None

    description = get_latest_dataset_description(dataset_id)

    status = get_latest_status_update(dataset_id)
    status_ = DatasetStatus(status["status"]) if status else DatasetStatus.IN_PROCESSING

    # Not sure which properties are set by this bit:
    # foreach( $this->xml_fields_dataset['csv'] as $field ) {
    #   $dataset->{$field} = getcsv( $dataset->{$field} );
    # }

    data_processed = get_latest_processing_update(dataset_id)
    if data_processed:
        date_processed = data_processed["processing_date"]
        warning = data_processed["warning"]
        error = data_processed["error"]
        if warning or error:
            msg = f"Dataset processed with {warning=} and {error=}. Behavior unclear."
            raise NotImplementedError(msg)
    else:
        date_processed = None

    return DatasetMetadata(
        id=dataset["did"],
        visibility=dataset["visibility"],
        status=status_,
        name=dataset["name"],
        licence=dataset["licence"],
        version=dataset["version"],
        version_label=dataset["version_label"] or "",
        language=dataset["language"] or "",
        creator=(dataset["creator"] or "").split(", "),
        contributor=(dataset["contributor"] or "").split(", "),
        citation=dataset["citation"] or "",
        upload_date=dataset["upload_date"],
        processing_date=date_processed,
        description=description["description"] if description else "",
        description_version=description["version"] if description else 0,
        tag=tags,
        default_target_attribute=dataset["default_target_attribute"],
        url=dataset_url,
        parquet_url=parquet_url,
        minio_url=parquet_url,
        file_id=dataset["file_id"],
        format=dataset["format"],
        original_data_url=dataset_url,
        md5_checksum=file["md5_hash"],
    )
