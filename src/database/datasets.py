"""Translation from https://github.com/openml/OpenML/blob/c19c9b99568c0fabb001e639ff6724b9a754bbc9/openml_OS/models/api/v1/Api_data.php#L707"""

import datetime

from sqlalchemy import Connection, text
from sqlalchemy.engine import Row

from schemas.datasets.openml import Feature


def get(id_: int, connection: Connection) -> Row | None:
    row = connection.execute(
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


def get_file(*, file_id: int, connection: Connection) -> Row | None:
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


def get_tags_for(id_: int, connection: Connection) -> list[str]:
    rows = connection.execute(
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


def tag(id_: int, tag_: str, *, user_id: int, connection: Connection) -> None:
    connection.execute(
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


def get_description(
    id_: int,
    connection: Connection,
) -> Row | None:
    """Get the most recent description for the dataset."""
    row = connection.execute(
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


def get_status(id_: int, connection: Connection) -> Row | None:
    """Get most recent status for the dataset."""
    row = connection.execute(
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


def get_features(dataset_id: int, connection: Connection) -> list[Feature]:
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


def get_feature_values(dataset_id: int, *, feature_index: int, connection: Connection) -> list[str]:
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


def update_status(
    dataset_id: int,
    status: str,
    *,
    user_id: int,
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


def insert_file(
    *,
    file_name: str,
    reference: str,
    md5_hash: str,
    connection: Connection,
) -> int:
    """Insert a row into the `file` table and return the new file id."""
    connection.execute(
        text(
            """
            INSERT INTO file(`name`, `reference`, `md5_hash`)
            VALUES (:name, :reference, :md5_hash)
            """,
        ),
        parameters={"name": file_name, "reference": reference, "md5_hash": md5_hash},
    )
    result = connection.execute(text("SELECT LAST_INSERT_ID()"))
    (file_id,) = result.one()
    return int(file_id)


def update_file_reference(
    *,
    file_id: int,
    reference: str,
    connection: Connection,
) -> None:
    """Update the MinIO object key on an existing file row."""
    connection.execute(
        text("UPDATE file SET `reference` = :reference WHERE `id` = :file_id"),
        parameters={"reference": reference, "file_id": file_id},
    )


def insert_dataset(  # noqa: PLR0913
    *,
    name: str,
    description: str,
    format_: str,
    file_id: int,
    uploader: int,
    visibility: str,
    licence: str,
    language: str,
    default_target_attribute: str,
    original_data_url: str,
    paper_url: str,
    collection_date: str,
    citation: str,
    md5_checksum: str,
    connection: Connection,
) -> int:
    """Insert a row into the `dataset` table and return the new dataset id."""
    connection.execute(
        text(
            """
            INSERT INTO dataset(
                `name`, `description`, `format`, `file_id`, `uploader`,
                `visibility`, `licence`, `language`,
                `default_target_attribute`, `original_data_url`, `paper_url`,
                `collection_date`, `citation`, `md5_checksum`,
                `version`, `upload_date`
            )
            VALUES (
                :name, :description, :format, :file_id, :uploader,
                :visibility, :licence, :language,
                :default_target_attribute, :original_data_url, :paper_url,
                :collection_date, :citation, :md5_checksum,
                1, NOW()
            )
            """,
        ),
        parameters={
            "name": name,
            "description": description,
            "format": format_,
            "file_id": file_id,
            "uploader": uploader,
            "visibility": visibility,
            "licence": licence,
            "language": language,
            "default_target_attribute": default_target_attribute,
            "original_data_url": original_data_url,
            "paper_url": paper_url,
            "collection_date": collection_date,
            "citation": citation,
            "md5_checksum": md5_checksum,
        },
    )
    result = connection.execute(text("SELECT LAST_INSERT_ID()"))
    (dataset_id,) = result.one()
    return int(dataset_id)


def insert_description(
    *,
    dataset_id: int,
    description: str,
    connection: Connection,
) -> None:
    """Insert the initial description into the `dataset_description` table."""
    connection.execute(
        text(
            """
            INSERT INTO dataset_description(`did`, `description`, `version`)
            VALUES (:did, :description, 1)
            """,
        ),
        parameters={"did": dataset_id, "description": description},
    )


def insert_features(
    *,
    dataset_id: int,
    features: list[dict[str, object]],
    connection: Connection,
) -> None:
    """Bulk-insert feature rows into `data_feature` in a single round-trip."""
    if not features:
        return
    connection.execute(
        text(
            """
            INSERT INTO data_feature(
                `did`, `index`, `name`, `data_type`,
                `is_target`, `is_row_identifier`, `is_ignore`,
                `NumberOfMissingValues`
            )
            VALUES (
                :did, :index, :name, :data_type,
                :is_target, :is_row_identifier, :is_ignore,
                :number_of_missing_values
            )
            """,
        ),
        [{"did": dataset_id, **feat} for feat in features],
    )


def insert_qualities(
    *,
    dataset_id: int,
    qualities: list[dict[str, object]],
    connection: Connection,
) -> None:
    """Bulk-insert quality rows into `data_quality` in a single round-trip."""
    if not qualities:
        return
    connection.execute(
        text(
            """
            INSERT INTO data_quality(`data`, `quality`, `value`)
            VALUES (:data, :quality, :value)
            """,
        ),
        [{"data": dataset_id, **q} for q in qualities],
    )
