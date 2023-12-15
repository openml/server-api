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
