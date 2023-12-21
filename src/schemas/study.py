from datetime import datetime
from enum import StrEnum, auto

from pydantic import BaseModel, Field

from schemas.core import Visibility


class StudyType(StrEnum):
    RUN = auto()
    TASK = auto()


class StudyStatus(StrEnum):
    ACTIVE = auto()
    DEACTIVATED = auto()
    IN_PREPARATION = auto()


class Study(BaseModel):
    _legacy: bool = Field(default=False, exclude=True)
    id_: int = Field(serialization_alias="id")
    name: str
    alias: str | None
    main_entity_type: StudyType
    description: str
    visibility: Visibility
    status: StudyStatus
    creation_date: datetime
    creator: int
    task_ids: list[int]
    run_ids: list[int]
    data_ids: list[int]
    setup_ids: list[int]
    flow_ids: list[int]


class CreateStudy(BaseModel):
    """Study, exposing only those fields that should be provided by the user on creation."""

    name: str = Field(
        description="Full name of the study.",
        examples=["The OpenML 100 Benchmarking Suite"],
        max_length=256,
    )
    alias: str | None = Field(
        default=None,
        description="Short alternative name for the study, which may be used to fetch it.",
        examples=["OpenML100"],
        max_length=32,
    )
    main_entity_type: StudyType = Field(
        default=StudyType.TASK,
        description="Whether it is a collection of runs (study) or tasks (benchmarking suite).",
        examples=[StudyType.TASK],
    )
    benchmark_suite: int | None = Field(
        # For study, refers to the benchmarking suite
        default=None,
        description="The benchmarking suite this study is based on, if any.",
    )
    description: str = Field(
        description=(
            "A good study description specifies why the study was created, what it is about, and "
            "how it should be used. It may include information about a related publication or"
            "website."
        ),
        examples=[
            (
                "A collection of tasks with simple datasets to benchmark machine learning methods."
                "Selected tasks are small classification problems that are not too imbalanced."
                "We advise the use of OpenML-CC18 instead, because OpenML100 suffers from some"
                "issues. If you do use OpeNML100, please cite ..."
            ),
        ],
        min_length=1,
        max_length=4096,
    )
    tasks: list[int] = Field(
        default_factory=list,
        description=(
            "Tasks to include in the study, can only be specified if `runs` is empty."
            "Can be modified later with `studies/{id}/attach` and `studies/{id}/detach`."
        ),
        examples=[[1, 2, 3]],
    )
    runs: list[int] = Field(
        default_factory=list,
        description=(
            "Runs to include in the study, can only be specified if `tasks` is empty."
            "Can be modified later with `studies/{id}/attach` and `studies/{id}/detach`."
        ),
        examples=[[]],
    )
