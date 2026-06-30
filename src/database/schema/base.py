"""Base classes for all ORM classes.

When defining a new ORM class, use both `Base` and one of the `DeferredReflection` subclasses to
make sure that the class is populated with attributes that may not be defined explicitly.
For example, when creating a new mapping for a table from the `openml_expdb` database, use:

class ClassName(ExpDBReflected, Base):
    __tablename__ = "class_names"

    # any columns you wanted mapped explicitly
    ...

"""

from sqlalchemy.ext.declarative import DeferredReflection
from sqlalchemy.orm import DeclarativeBase

from database.setup import expdb_database, user_database


class Base(DeclarativeBase):
    """Base class for all ORM classes."""


class ExpDBReflected(DeferredReflection):
    """Base class for ORM classes to map onto a table in the `openml_expdb` database."""

    __abstract__ = True


class UserDBReflected(DeferredReflection):
    """Base class for ORM classes to map onto a table in the `openml` database."""

    __abstract__ = True


async def reflect_db_schemas() -> None:
    """Populate defined ORM classes with attributes defined from columns in the database.

    For example, the `dataset` class would automatically get a `collection_date` attribute,
    even if it wasn't explicitly declared in the class definition,
    because the `openml_expdb.dataset` table has a column `collection_date`.
    """
    async with user_database().connect() as connection:
        await connection.run_sync(UserDBReflected.prepare)  # type: ignore[arg-type]  # run_sync expects positional-only arg but `prepare` does not have it.
    async with expdb_database().connect() as connection:
        await connection.run_sync(ExpDBReflected.prepare)  # type: ignore[arg-type]  # as above.
