"""Pydantic schemas for run-related endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class TraceIteration(BaseModel):
    """A single trace iteration for a run."""

    repeat: int
    fold: int
    iteration: int
    setup_string: str | None
    evaluation: float | None
    selected: str


class RunTrace(BaseModel):
    """Trace data for a run."""

    run_id: int
    trace: list[TraceIteration]


class ParameterSetting(BaseModel):
    """A single hyperparameter value used in a run's setup.

    `component` is the `implementation_id` of the flow that defines this
    parameter — useful when a setup spans multiple sub-flows (components).
    `value` is None when the parameter was not explicitly set (uses default).
    """

    name: str
    value: str | None
    component: int  # = input.implementation_id (flow_id of the owning component)


class InputDataset(BaseModel):
    """A dataset used as input for a run.

    Sourced from `input_data` JOIN `dataset`. `name` and `url` are fetched
    from the `dataset` table and match the values PHP returns.
    """

    did: int
    name: str
    url: str  # ARFF download URL stored in dataset.url


class OutputFile(BaseModel):
    """An output file produced by or attached to a run.

    Sourced from the `runfile` table. `name` is the file label
    (e.g. "description", "predictions").

    Note: the legacy PHP response included a `did` field hardcoded to "-1"
    for every entry here. It originates from a deprecated idea that run outputs
    could create new datasets. It is intentionally omitted in this implementation.
    """

    file_id: int
    name: str  # label as stored in runfile.field, e.g. "description", "predictions"


class EvaluationScore(BaseModel):
    """An evaluation metric score for a run.

    Sourced from a JOIN of `evaluation` and `math_function`.
    `array_data` holds per-fold/per-class breakdowns when available;
    `value` holds the aggregate scalar.

    Note: the `evaluation` table does NOT contain `repeat` or `fold` columns.
    Only aggregate metrics are available. (Confirmed against the PHP query
    in issue #37 which also only selects name, value, array_data.)
    """

    name: str
    value: float | int | None  # whole numbers returned as int to match PHP
    array_data: str | None


class Run(BaseModel):
    """Full metadata response for a single OpenML run.

    Notes:
    - `error_message` is serialized as "error".
    - `error_message` is [] (empty list) when the DB column is NULL.
    - `task_evaluation_measure` is omitted when null or empty.

    """

    model_config = ConfigDict(populate_by_name=True)

    run_id: int
    uploader: int  # user ID of the uploader
    uploader_name: str | None  # fetched from the separate openml DB (users table)
    task_id: int
    task_type: str | None  # e.g. "Supervised Classification"
    task_evaluation_measure: str | None  # omitted when null/empty (not returned)
    flow_id: int  # = algorithm_setup.implementation_id
    flow_name: str | None  # = implementation.fullName
    setup_id: int  # = algorithm_setup.sid
    setup_string: str | None  # human-readable description of the setup
    parameter_setting: list[ParameterSetting]
    # Serialized as "error" in JSON to match the PHP response key.
    # At the Python level we keep the name error_message for clarity.
    error_message: list[str] = Field(serialization_alias="error")  # [] when NULL in DB
    tag: list[str]
    input_data: dict[str, list[InputDataset]]  # {"dataset": [...]}
    output_data: dict[
        str,
        list[OutputFile | EvaluationScore],
    ]  # {"file": [...], "evaluation": [...]}
