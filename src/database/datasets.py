import datetime
import re
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncConnection

from routers.types import integer_range_regex
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
    row = await connection.execute(
        text(
            """
    SELECT *
    FROM dataset_tag
    WHERE id = :dataset_id
    """,
        ),
        parameters={"dataset_id": id_},
    )
    rows = row.all()
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
    return row.first()


async def get_features(dataset_id: int, connection: AsyncConnection) -> list[Feature]:
    row = await connection.execute(
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
    rows = row.mappings().all()
    return [Feature(**row, nominal_values=None) for row in rows]


async def get_feature_ontologies(
    dataset_id: int,
    connection: AsyncConnection,
) -> dict[int, list[str]]:
    rows = await connection.execute(
        text(
            """
            SELECT `index`, `value`
            FROM data_feature_description
            WHERE `did` = :dataset_id AND `description_type` = 'ontology'
            """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    ontologies: dict[int, list[str]] = {}
    for mapping in rows.mappings():
        index = int(mapping["index"])
        value = str(mapping["value"])
        if index not in ontologies:
            ontologies[index] = []
        ontologies[index].append(value)
    return ontologies


async def get_feature_values(
    dataset_id: int,
    *,
    feature_index: int,
    connection: AsyncConnection,
) -> list[str]:
    row = await connection.execute(
        text(
            """
            SELECT `value`
            FROM data_feature_value
            WHERE `did` = :dataset_id AND `index` = :feature_index
            """,
        ),
        parameters={"dataset_id": dataset_id, "feature_index": feature_index},
    )
    rows = row.all()
    return [row.value for row in rows]


async def get_feature_values_bulk(
    dataset_id: int,
    connection: AsyncConnection,
) -> dict[int, list[str]]:
    rows = await connection.execute(
        text(
            """
            SELECT `index`, `value`
            FROM data_feature_value
            WHERE `did` = :dataset_id
            """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    values: dict[int, list[str]] = {}
    for mapping in rows.mappings():
        index = int(mapping["index"])
        value = str(mapping["value"])
        if index not in values:
            values[index] = []
        values[index].append(value)
    return values


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
            "date": datetime.datetime.now(datetime.UTC),
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


async def list_datasets(  # noqa: C901, PLR0913
    *,
    limit: int,
    offset: int,
    data_name: str | None = None,
    data_version: str | None = None,
    tag: str | None = None,
    data_ids: list[int] | None = None,
    uploader: int | None = None,
    number_instances: str | None = None,
    number_features: str | None = None,
    number_classes: str | None = None,
    number_missing_values: str | None = None,
    statuses: list[str],
    user_id: int | None = None,
    is_admin: bool = False,
    connection: AsyncConnection,
) -> Sequence[Row]:
    current_status = """
        SELECT ds1.`did`, ds1.`status`
        FROM dataset_status AS ds1
        WHERE ds1.`status_date`=(
            SELECT MAX(ds2.`status_date`)
            FROM dataset_status as ds2
            WHERE ds1.`did`=ds2.`did`
        )
    """

    if is_admin:
        visible_to_user = "TRUE"
    elif user_id:
        visible_to_user = f"(`visibility`='public' OR `uploader`={user_id})"
    else:
        visible_to_user = "`visibility`='public'"

    where_name = "AND `name`=:data_name" if data_name else ""
    where_version = "AND `version`=:data_version" if data_version else ""
    where_uploader = "AND `uploader`=:uploader" if uploader else ""
    where_data_id = "AND d.`did` IN :data_ids" if data_ids else ""

    matching_tag = (
        """
        AND d.`did` IN (
            SELECT `id`
            FROM dataset_tag as dt
            WHERE dt.`tag`=:tag
        )
        """
        if tag
        else ""
    )

    def quality_clause(quality: str, range_str: str | None, param_name: str) -> str:
        if not range_str:
            return ""
        if not (match := re.match(integer_range_regex, range_str)):
            msg = f"`range_str` not a valid range: {range_str}"
            raise ValueError(msg)
        _start, end = match.groups()
        if end:
            # end is e.g. "..150"
            value = f"`value` BETWEEN :{param_name}_start AND :{param_name}_end"
        else:
            value = f"`value` = :{param_name}_start"

        return f""" AND
            d.`did` IN (
                SELECT `data`
                FROM data_quality
                WHERE `quality`='{quality}' AND {value}
            )
        """  # noqa: S608

    q_params = {}

    def get_range_params(range_str: str | None, param_prefix: str) -> dict[str, Any]:
        if not range_str:
            return {}
        if not (match := re.match(integer_range_regex, range_str)):
            return {}
        _start, end = match.groups()
        params: dict[str, Any] = {f"{param_prefix}_start": _start}
        if end:
            # end is e.g. "..150"
            end_val = str(end)
            params[f"{param_prefix}_end"] = end_val[2:]
        return params

    instances_filter = quality_clause("NumberOfInstances", number_instances, "instances")
    q_params.update(get_range_params(number_instances, "instances"))

    features_filter = quality_clause("NumberOfFeatures", number_features, "features")
    q_params.update(get_range_params(number_features, "features"))

    classes_filter = quality_clause("NumberOfClasses", number_classes, "classes")
    q_params.update(get_range_params(number_classes, "classes"))

    missing_values_filter = quality_clause(
        "NumberOfMissingValues",
        number_missing_values,
        "missing_values",
    )
    q_params.update(get_range_params(number_missing_values, "missing_values"))

    sql = text(
        f"""
        SELECT d.`did`, d.`name`, d.`version`, d.`format`, d.`file_id`,
               IFNULL(cs.`status`, 'in_preparation') AS status
        FROM dataset AS d
        LEFT JOIN ({current_status}) AS cs ON d.`did`=cs.`did`
        WHERE {visible_to_user} {where_name} {where_version} {where_uploader}
        {where_data_id} {matching_tag} {instances_filter} {features_filter}
        {classes_filter} {missing_values_filter}
        AND IFNULL(cs.`status`, 'in_preparation') IN :statuses
        LIMIT :limit OFFSET :offset
        """,  # noqa: S608
    )

    parameters = {
        "data_name": data_name,
        "data_version": data_version,
        "uploader": uploader,
        "tag": tag,
        "statuses": statuses,
        "limit": limit,
        "offset": offset,
        **q_params,
    }
    if data_ids:
        parameters["data_ids"] = data_ids

    result = await connection.execute(
        sql.bindparams(statuses=statuses, data_ids=data_ids) if data_ids else sql,
        parameters=parameters,
    )
    return cast("Sequence[Row]", result.all())
