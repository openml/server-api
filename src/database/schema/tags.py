"""ORM classes for the *_tag tables (task_tag, ...)."""

from datetime import datetime

from sqlalchemy import FetchedValue
from sqlalchemy.orm import Mapped, mapped_column

from database.schema.base import Base, ExpDBReflected
from routers.types import Identifier, TagString


class Tag:
    """Base class for all of the *_tag tables."""

    # The identifier of the entity that is tagged (e.g., dataset id, task id)
    entity_id: Mapped[Identifier] = mapped_column("id", primary_key=True)
    tag: Mapped[TagString] = mapped_column(primary_key=True)
    uploader_id: Mapped[Identifier] = mapped_column("uploader")
    creation_date: Mapped[datetime] = mapped_column("date", server_default=FetchedValue())


class TaskTag(ExpDBReflected, Tag, Base):
    """Tags belonging to a task."""

    __tablename__ = "task_tag"

    @property
    def task_id(self) -> Identifier:
        """Identifier of the task which is tagged by this tag."""
        return self.entity_id
