import json
import re
from enum import StrEnum
from typing import Annotated, Any, cast

import xmltodict
from fastapi import APIRouter, Body, Depends
from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncConnection

import config
import database.datasets
import database.tasks
from core.errors import InternalError, NoResultsError, TaskNotFoundError
from routers.dependencies import Pagination, expdb_connection
from routers.types import CasualString128, IntegerRange, SystemString64, integer_range_regex
from schemas.datasets.openml import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])

type JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None


def convert_template_xml_to_json(xml_template: str) -> dict[str, JSON]:
    json_template = xmltodict.parse(xml_template.replace("oml:", ""))
    json_str = json.dumps(json_template)
    # To account for the differences between PHP and Python conversions:
    for py, php in [("@name", "name"), ("#text", "value"), ("@type", "type")]:
        json_str = json_str.replace(py, php)
    return cast("dict[str, JSON]", json.loads(json_str))


async def fill_template(
    template: str,
    task: RowMapping,
    task_inputs: dict[str, str | int],
    connection: AsyncConnection,
) -> dict[str, JSON]:
    """Fill in the XML template as used for task descriptions and return the result.

    The result is converted to JSON.

    template, str:
        A string represent XML, as detailed below.
    task, ?:
        The `task` for which to fill in the template.
    task_inputs, dict:
        The `task_input` entries where keys correspond to `input` and values
        correspond to `value`.

    returns: str
        The template with values filled in.


    The template is an XML template that specifies which information to show to the user,
    and where to fetch it from. For example:

    <oml:estimation_procedure>
      <oml:id>[INPUT:estimation_procedure]</oml:id>
      <oml:type>[LOOKUP:estimation_procedure.type]</oml:type>
      <oml:data_splits_url>[CONSTANT:base_url]api_splits/get/[TASK:id]/Task_[TASK:id]_splits.arff</oml:data_splits_url>
      <oml:parameter name="number_repeats">[LOOKUP:estimation_procedure.repeats]</oml:parameter>
      <oml:parameter name="number_folds">[LOOKUP:estimation_procedure.folds]</oml:parameter>
    </oml:estimation_procedure>

    Here, we encounter the following directives:
      - [INPUT:X] specifies that should be replaced by the `value` from the
        `task_inputs` table where `input`=X.
      - [LOOKUP:A.B] specifies that it should be replaced by the value in
        column `B` of table `A` in the row where `A.id` equals the `value`
        from the `task_inputs` table where `input`=A.
      - [CONSTANT:a] is replaced by a constant 'a' known by the PHP API.
      - [TASK:id] is replaced by the task id.

    Resulting JSON could look like:

    "estimation_procedure": {
        "id": 5,
        "type": "crossvalidation",
        "data_splits_url": "https://test.openml.org/api_splits/get/1/Task_1_splits.arff"
        "parameter": [
            {"name": "number_repeats", "value": 1},
            {"name": "number_folds", "value: 10},
        ]
    }
    """
    json_template = convert_template_xml_to_json(template)
    return cast(
        "dict[str, JSON]",
        await _fill_json_template(
            json_template,
            task,
            task_inputs,
            fetched_data={},
            connection=connection,
        ),
    )


async def _fill_json_template(  # noqa: C901
    template: JSON,
    task: RowMapping,
    task_inputs: dict[str, str | int],
    fetched_data: dict[str, str],
    connection: AsyncConnection,
) -> JSON:
    if isinstance(template, dict):
        return {
            k: await _fill_json_template(v, task, task_inputs, fetched_data, connection)
            for k, v in template.items()
        }
    if isinstance(template, list):
        return [
            await _fill_json_template(v, task, task_inputs, fetched_data, connection)
            for v in template
        ]
    if not isinstance(template, str):
        msg = f"Unexpected type for `template`: {template=}, {type(template)=}"
        raise TypeError(msg)

    # I believe at this point, if there is an [INPUT:] or [LOOKUP:] directive,
    # this is always the entirety of the string. However, for now we verify explicitly.
    if match := re.search(r"\[INPUT:(.*)]", template):
        (field,) = match.groups()
        if match.string == template:
            # How do we know the default value? probably ttype_io table?
            return task_inputs.get(field, [])
        template = template.replace(match.group(), str(task_inputs[field]))
    if match := re.search(r"\[LOOKUP:(.*)]", template):
        (field,) = match.groups()
        if field not in fetched_data:
            table, _ = field.split(".")
            result = await connection.execute(
                text(
                    f"""
                    SELECT *
                    FROM {table}
                    WHERE `id` = :id_
                    """,  # noqa: S608
                ),
                # Not sure how parametrize table names, as the parametrization adds
                # quotes which is not legal.
                parameters={"id_": int(task_inputs[table])},
            )
            rows = result.mappings()
            row_data = next(rows, None)
            if row_data is None:
                msg = f"No data found for table {table} with id {task_inputs[table]}"
                raise ValueError(msg)
            for column, value in row_data.items():
                fetched_data[f"{table}.{column}"] = value
        if match.string == template:
            return fetched_data[field]
        template = template.replace(match.group(), fetched_data[field])
    # I believe that the operations below are always part of string output, so
    # we don't need to be careful to avoid losing typedness
    template = template.replace("[TASK:id]", str(task.task_id))
    server_url = config.load_routing_configuration()["server_url"]
    return template.replace("[CONSTANT:base_url]", server_url)


class TaskStatusFilter(StrEnum):
    """Valid values for the status filter."""

    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    IN_PREPARATION = "in_preparation"
    ALL = "all"


QUALITIES_TO_SHOW = [
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

BASIC_TASK_INPUTS = [
    "source_data",
    "target_feature",
    "estimation_procedure",
    "evaluation_measures",
]


def _quality_clause(quality: str, range_: str | None) -> str:
    """Return a SQL WHERE clause fragment filtering tasks by a dataset quality range.

    Looks up tasks whose source dataset has the given quality within the range.
    Range can be exact ('100') or a range ('50..200').
    """
    if not range_:
        return ""
    if not (match := re.match(integer_range_regex, range_)):
        msg = f"`range_` not a valid range: {range_}"
        raise ValueError(msg)
    start, end = match.groups()
    # end group looks like "..200", strip the ".." prefix to get just the number
    value = f"`value` BETWEEN {start} AND {end[2:]}" if end else f"`value`={start}"
    # nested subquery: find datasets with matching quality, then find tasks using those datasets
    return f"""
        AND t.`task_id` IN (
            SELECT ti.`task_id` FROM task_inputs ti
            WHERE ti.`input`='source_data' AND ti.`value` IN (
                SELECT `data` FROM data_quality
                WHERE `quality`='{quality}' AND {value}
            )
        )
    """  # noqa: S608


@router.post(path="/list", description="Provided for convenience, same as `GET` endpoint.")
@router.get(path="/list")
async def list_tasks(  # noqa: PLR0913
    pagination: Annotated[Pagination, Body(default_factory=Pagination)],
    task_type_id: Annotated[int | None, Body(description="Filter by task type id.")] = None,
    tag: Annotated[str | None, SystemString64] = None,
    data_tag: Annotated[str | None, SystemString64] = None,
    status: Annotated[TaskStatusFilter, Body()] = TaskStatusFilter.ACTIVE,
    task_id: Annotated[list[int] | None, Body(description="Filter by task id(s).")] = None,
    data_id: Annotated[list[int] | None, Body(description="Filter by dataset id(s).")] = None,
    data_name: Annotated[str | None, CasualString128] = None,
    number_instances: Annotated[str | None, IntegerRange] = None,
    number_features: Annotated[str | None, IntegerRange] = None,
    number_classes: Annotated[str | None, IntegerRange] = None,
    number_missing_values: Annotated[str | None, IntegerRange] = None,
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)] = None,
) -> list[dict[str, Any]]:
    """List tasks, optionally filtered by type, tag, status, dataset properties, and more."""
    assert expdb is not None  # noqa: S101

    # --- WHERE clauses ---
    if status == TaskStatusFilter.ALL:
        where_status = ""
    else:
        where_status = f"AND IFNULL(ds.`status`, 'in_preparation') = '{status}'"

    where_type = "" if task_type_id is None else "AND t.`ttid` = :task_type_id"
    where_tag = (
        "" if tag is None else "AND t.`task_id` IN (SELECT `id` FROM task_tag WHERE `tag` = :tag)"
    )
    where_data_tag = (
        ""
        if data_tag is None
        else "AND d.`did` IN (SELECT `id` FROM dataset_tag WHERE `tag` = :data_tag)"
    )
    task_id_str = ",".join(str(tid) for tid in task_id) if task_id else ""
    where_task_id = "" if not task_id else f"AND t.`task_id` IN ({task_id_str})"
    data_id_str = ",".join(str(did) for did in data_id) if data_id else ""
    where_data_id = "" if not data_id else f"AND d.`did` IN ({data_id_str})"
    where_data_name = "" if data_name is None else "AND d.`name` = :data_name"

    where_number_instances = _quality_clause("NumberOfInstances", number_instances)
    where_number_features = _quality_clause("NumberOfFeatures", number_features)
    where_number_classes = _quality_clause("NumberOfClasses", number_classes)
    where_number_missing_values = _quality_clause("NumberOfMissingValues", number_missing_values)

    basic_inputs_str = ", ".join(f"'{i}'" for i in BASIC_TASK_INPUTS)

    # subquery to get the latest status per dataset
    # dataset_status has multiple rows per dataset (history), we want only the most recent
    status_subquery = """
        SELECT ds1.did, ds1.status
        FROM dataset_status ds1
        WHERE ds1.status_date = (
            SELECT MAX(ds2.status_date) FROM dataset_status ds2
            WHERE ds1.did = ds2.did
        )
    """

    query = text(
        f"""
        SELECT
            t.`task_id`,
            t.`ttid` AS task_type_id,
            tt.`name` AS task_type,
            d.`did`,
            d.`name`,
            d.`format`,
            IFNULL(ds.`status`, 'in_preparation') AS status
        FROM task t
        JOIN task_type tt ON tt.`ttid` = t.`ttid`
        JOIN task_inputs ti_source ON ti_source.`task_id` = t.`task_id`
            AND ti_source.`input` = 'source_data'
        JOIN dataset d ON d.`did` = ti_source.`value`
        LEFT JOIN ({status_subquery}) ds ON ds.`did` = d.`did`
        WHERE 1=1
            {where_status}
            {where_type}
            {where_tag}
            {where_data_tag}
            {where_task_id}
            {where_data_id}
            {where_data_name}
            {where_number_instances}
            {where_number_features}
            {where_number_classes}
            {where_number_missing_values}
        GROUP BY t.`task_id`, t.`ttid`, tt.`name`, d.`did`, d.`name`, d.`format`, ds.`status`
        LIMIT {pagination.limit} OFFSET {pagination.offset}
        """,  # noqa: S608
    )

    result = await expdb.execute(
        query,
        parameters={
            "task_type_id": task_type_id,
            "tag": tag,
            "data_tag": data_tag,
            "data_name": data_name,
        },
    )
    rows = result.mappings().all()

    if not rows:
        msg = "No tasks match the search criteria."
        raise NoResultsError(msg)

    columns = ["task_id", "task_type_id", "task_type", "did", "name", "format", "status"]
    tasks: dict[int, dict[str, Any]] = {
        row["task_id"]: {col: row[col] for col in columns} for row in rows
    }

    # fetch inputs for all tasks in one query
    task_ids_str = ",".join(str(tid) for tid in tasks)
    inputs_result = await expdb.execute(
        text(
            f"""
            SELECT `task_id`, `input`, `value`
            FROM task_inputs
            WHERE `task_id` IN ({task_ids_str})
            AND `input` IN ({basic_inputs_str})
            """,  # noqa: S608
        ),
    )
    for row in inputs_result.all():
        tasks[row.task_id].setdefault("input", []).append(
            {"name": row.input, "value": row.value},
        )

    # fetch qualities for all datasets in one query
    did_list = ",".join(str(t["did"]) for t in tasks.values())
    qualities_str = ", ".join(f"'{q}'" for q in QUALITIES_TO_SHOW)
    qualities_result = await expdb.execute(
        text(
            f"""
            SELECT `data`, `quality`, `value`
            FROM data_quality
            WHERE `data` IN ({did_list})
            AND `quality` IN ({qualities_str})
            """,  # noqa: S608
        ),
    )
    # build a reverse map: dataset_id -> task_id
    # needed because quality rows come back keyed by did, but our tasks dict is keyed by task_id
    did_to_task_id = {t["did"]: tid for tid, t in tasks.items()}
    for row in qualities_result.all():
        tid = did_to_task_id.get(row.data)
        if tid is not None:
            tasks[tid].setdefault("quality", []).append(
                {"name": row.quality, "value": str(row.value)},
            )

    # fetch tags for all tasks in one query
    tags_result = await expdb.execute(
        text(
            f"""
            SELECT `id`, `tag`
            FROM task_tag
            WHERE `id` IN ({task_ids_str})
            """,  # noqa: S608
        ),
    )
    for row in tags_result.all():
        tasks[row.id].setdefault("tag", []).append(row.tag)

    # ensure every task has all expected keys(input/quality/tag) even if no rows were found for them
    # e.g. a task with no tags should return "tag": [] not missing key
    for task in tasks.values():
        task.setdefault("input", [])
        task.setdefault("quality", [])
        task.setdefault("tag", [])

    return list(tasks.values())


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> Task:
    if not (task := await database.tasks.get(task_id, expdb)):
        msg = f"Task {task_id} not found."
        raise TaskNotFoundError(msg)
    if not (task_type := await database.tasks.get_task_type(task.ttid, expdb)):
        msg = f"Task {task_id} has task type {task.ttid}, but task type {task.ttid} is not found."
        raise InternalError(msg)

    task_inputs = {
        row.input: int(row.value) if row.value.isdigit() else row.value
        for row in await database.tasks.get_input_for_task(task_id, expdb)
    }
    ttios = await database.tasks.get_task_type_inout_with_template(task_type.ttid, expdb)
    templates = [(tt_io.name, tt_io.io, tt_io.requirement, tt_io.template_api) for tt_io in ttios]
    inputs = [
        await fill_template(template, task, task_inputs, expdb) | {"name": name}
        for name, io, required, template in templates
        if io == "input"
    ]
    outputs = [
        convert_template_xml_to_json(template) | {"name": name}
        for name, io, required, template in templates
        if io == "output"
    ]
    tags = await database.tasks.get_tags(task_id, expdb)
    name = f"Task {task_id} ({task_type.name})"
    dataset_id = task_inputs.get("source_data")
    if isinstance(dataset_id, int) and (dataset := await database.datasets.get(dataset_id, expdb)):
        name = f"Task {task_id}: {dataset.name} ({task_type.name})"

    return Task(
        id_=task.task_id,
        name=name,
        task_type_id=task.ttid,
        task_type=task_type.name,
        input_=inputs,
        output=outputs,
        tags=tags,
    )
