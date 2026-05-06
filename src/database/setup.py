from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config import DatabaseConfiguration, get_config

_user_engine = None
_expdb_engine = None


def _create_engine(db_config: DatabaseConfiguration) -> AsyncEngine:
    db_url = URL.create(
        drivername=db_config.drivername,
        username=db_config.username,
        password=db_config.password,
        host=db_config.host,
        database=db_config.database,
    )
    return create_async_engine(
        db_url,
        echo=db_config.echo,
        pool_recycle=3600,
    )


def user_database() -> AsyncEngine:
    global _user_engine  # noqa: PLW0603
    if _user_engine is None:
        _user_engine = _create_engine(get_config().openml_database)
    return _user_engine


def expdb_database() -> AsyncEngine:
    global _expdb_engine  # noqa: PLW0603
    if _expdb_engine is None:
        _expdb_engine = _create_engine(get_config().expdb_database)
    return _expdb_engine


async def close_databases() -> None:
    """Close all database connections."""
    global _user_engine, _expdb_engine  # noqa: PLW0603
    if _user_engine is not None:
        await _user_engine.dispose()
        _user_engine = None
    if _expdb_engine is not None:
        await _expdb_engine.dispose()
        _expdb_engine = None
