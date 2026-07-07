"""Setup ORM Model."""

from sqlalchemy.orm import Mapped, mapped_column

from database.schema.base import Base, ExpDBReflected
from routers.types import Identifier


class Setup(ExpDBReflected, Base):
    """Specifies the hyperparameter configuration of a Flow used in a Run."""

    __tablename__ = "algorithm_setup"
    id: Mapped[Identifier] = mapped_column("sid", primary_key=True)
    flow_id: Mapped[Identifier] = mapped_column("implementation_id")

    setup_string: Mapped[str]
