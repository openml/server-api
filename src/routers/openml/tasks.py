# ruff: noqa: D100, D103
import json
import re
from typing import Annotated, cast

import xmltodict
from fastapi import APIRouter, Depends
from sqlalchemy import Connection, RowMapping, text

import config
import database.datasets
import database.tasks
from core.errors import InternalError, TaskNotFoundError
from routers.dependencies import expdb_connection
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


def fill_template(
    template: str,
    task: RowMapping,
    task_inputs: dict[str, str | int],
    connection: Connection,
) -> dict[str, JSON]:
    """Fill in the XML template used for task descriptions.

    Return the result converted to JSON.

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
        _fill_json_template(
            json_template,
            task,
            task_inputs,
            fetched_data={},
            connection=connection,
        ),
    )


def _fill_json_template(
    template: JSON,
    task: RowMapping,
    task_inputs: dict[str, str | int],
    fetched_data: dict[str, str],
    connection: Connection,
) -> JSON:
    if isinstance(template, dict):
        return {
            k: _fill_json_template(v, task, task_inputs, fetched_data, connection)
            for k, v in template.items()
        }
    if isinstance(template, list):
        return [
            _fill_json_template(v, task, task_inputs, fetched_data, connection) for v in template
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
            rows = connection.execute(
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
            for column, value in next(rows.mappings()).items():
                fetched_data[f"{table}.{column}"] = value
        if match.string == template:
            return fetched_data[field]
        template = template.replace(match.group(), fetched_data[field])
    # I believe that the operations below are always part of string output, so
    # we don't need to be careful to avoid losing typedness
    template = template.replace("[TASK:id]", str(task.task_id))
    server_url = config.load_routing_configuration()["server_url"]
    return template.replace("[CONSTANT:base_url]", server_url)


@router.get("/{task_id}")
def get_task(
    task_id: int,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> Task:
    if not (task := database.tasks.get(task_id, expdb)):
        msg = "Task not found."
        raise TaskNotFoundError(msg)
    if not (task_type := database.tasks.get_task_type(task.ttid, expdb)):
        msg = "Task type not found."
        raise InternalError(msg)

    task_inputs = {
        row.input: int(row.value) if row.value.isdigit() else row.value
        for row in database.tasks.get_input_for_task(task_id, expdb)
    }
    ttios = database.tasks.get_task_type_inout_with_template(task_type.ttid, expdb)
    templates = [(tt_io.name, tt_io.io, tt_io.requirement, tt_io.template_api) for tt_io in ttios]
    inputs = [
        fill_template(template, task, task_inputs, expdb) | {"name": name}
        for name, io, required, template in templates
        if io == "input"
    ]
    outputs = [
        convert_template_xml_to_json(template) | {"name": name}
        for name, io, required, template in templates
        if io == "output"
    ]
    tags = database.tasks.get_tags(task_id, expdb)
    name = f"Task {task_id} ({task_type.name})"
    dataset_id = task_inputs.get("source_data")
    if isinstance(dataset_id, int) and (dataset := database.datasets.get(dataset_id, expdb)):
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
