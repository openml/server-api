import re
from typing import Any, Annotated

from fastapi import APIRouter, Depends
from pydantic import Json
from sqlalchemy import Connection, text

from database.datasets import get_dataset
from database.users import User
from routers.dependencies import fetch_user, expdb_connection
from schemas.datasets.openml import Task
import xmltodict


router = APIRouter(prefix="/tasks", tags=["tasks"])


def convert_template(xml_template: str) -> Json:
    json_template = xmltodict.parse(xml_template.replace("oml:", ""))
    # To account for the differences between PHP and Python conversions:
    inner_dict = list(json_template.values())[0]
    for parameter in inner_dict.get("parameter", []):
        parameter["name"] = parameter.pop("@name")
        parameter["value"] = parameter.pop("#text")
    return json_template


def fill_template(template: str, task, task_inputs, connection: Connection):
    """ Fill in the XML template as used for task descriptions.

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
      <oml:data_splits_url>[CONSTANT:base_url]api_splits/get/[TASK:id]/Task_[TASK:id]_splits.arff</oml:data_splits_url>  # noqa: E501
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
    fetched_data = {}
    lines = []
    for line in template.splitlines():
        if match := re.search(r"\[INPUT:(.*)]", line):
            (field,) = match.groups()
            # Does it need to exist, or can it be unspecified? i.e. [x] vs .get(x)
            line = line.replace(match.group(), task_inputs[field])
        if match := re.search(r"\[LOOKUP:(.*)]", line):
            (field,) = match.groups()
            if field not in fetched_data:
                table, _ = field.split(".")
                rows = connection.execute(
                    text(
                        f"""
                        SELECT *
                        FROM {table}
                        WHERE `id` = :id_
                        """
                    ), parameters={"id_": int(task_inputs[table])}
                )
                for column, value in next(rows.mappings()).items():
                    # Because of string replacement, the value needs to be a string
                    # can not easily rectify without first converting the XML to JSON
                    fetched_data[f"{table}.{column}"] = str(value)
            line = line.replace(match.group(), fetched_data[field])
        line = line.replace("[TASK:id]", str(task.task_id))
        line = line.replace("[CONSTANT:base_url]", "get_the_right_base_url")
        lines.append(line)
    return '\n'.join(lines)


@router.get("/{task_id}")
def get_task(
    task_id: int,
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> Task:
    # fetch primary task metadata
    task_row = expdb.execute(
        text(
            """
            SELECT *
            FROM task
            WHERE `task_id` = :task_id
            """
        ), parameters={"task_id": task_id}
    )
    task = next(task_row.mappings())
    # fetch secondary task metadata
    task_type_row = expdb.execute(
        text(
            """
            SELECT * 
            FROM task_type
            WHERE `ttid` = :task_type_id
            """
        ), parameters={"task_type_id": task.ttid}
    )
    task_type = next(task_type_row)
    input_rows = expdb.execute(
        text(
            """
            SELECT `input`, `value`
            FROM task_inputs
            WHERE task_id = :task_id
            """
        ), parameters={"task_id": task_id}
    )
    inputs = {row.input: row.value for row in input_rows}
    ttios = expdb.execute(
        text(
            """
            SELECT *
            FROM task_type_inout
            WHERE `ttid` = :task_type_id AND `template_api` IS NOT NULL
            """
        ), parameters={"task_type_id": task.ttid}
    )
    # breakpoint()
    # Have a look at "hidden" requirements. Do we ignore them at this stage?
    # templates = [
    #     (tt_io.name, tt_io.io, tt_io.requirement, tt_io.template)
    #     for tt_io in ttios
    # ]
    # inputs = [
    #     fill_template(template, task, )
    #     for name, io, required, template in templates
    #     if io == "input" and (required == "required" or name in inputs)
    # ]
    # outputs = [
    #     fill_template(template)
    #     for name, io, required, template in templates
    #     if io == "output"
    # ]
    fs = []
    for tt_io in ttios:
        if tt_io.name not in inputs and tt_io.requirement == "optional":
            continue
        fs.append(fill_template(
            tt_io.template_api,
            task,
            inputs,
            expdb,
        ))
    breakpoint()
    # def get_task_input_output():
    #     ttios = expdb.execute(
    #         text(
    #             """
    #             SELECT *
    #             FROM task_type_inout
    #             WHERE `ttid` = :task_type_id AND `template_api` IS NOT NULL
    #             """
    #         ), parameters={"task_type_id": task.ttid}
    #     )
    #     for tt_io in ttios:
    #         tt_io.template_api
    #         {
    #             "name": tt_io.name,
    #             <template>
    #         }
    # for table, identifier in inputs.items():
    #     ...
    # [CONSTANT: base_url]api_splits / get / [TASK: id] / Task_[TASK:id]
    # _splits.arff
    # if custom_testset is part, then raise error
    # get tasktype io
    tag_rows = expdb.execute(
        text(
            """
            SELECT `tag`
            FROM task_tag
            WHERE `id` = :task_id 
            """
        ), parameters={"task_id": task_id}
    )
    tags = [row.tag for row in tag_rows]
    name = f"Task {task_id} ({task_type.name})"
    if dataset_id := inputs.get("source_data"):
        dataset = get_dataset(dataset_id, expdb)
        name = f"Task {task_id}:  {dataset['name']} ({task_type.name})"

    return Task(
        id_=task.task_id,
        name=name,
        task_type_id=task.ttid,
        task_type=task_type.name,
        input_=[inputs],
        output={},
        tags=tags,
    )
