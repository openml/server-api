from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.engine import URL

from config import load_database_configuration

_user_engine = None
_expdb_engine = None


def _create_engine(database_name: str) -> AsyncEngine:
    database_configuration = load_database_configuration()
    echo = database_configuration[database_name].pop("echo", False)
    db_url = URL.create(**database_configuration[database_name])
    return create_async_engine(
        db_url,
        echo=echo,
        pool_recycle=3600,
    )


def user_database() -> AsyncEngine:
    global _user_engine  # noqa: PLW0603
    if _user_engine is None:
        _user_engine = _create_engine("openml")
    return _user_engine


def expdb_database() -> AsyncEngine:
    global _expdb_engine  # noqa: PLW0603
    if _expdb_engine is None:
        _expdb_engine = _create_engine("expdb")
    return _expdb_engine
