import functools

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config import DatabaseConfiguration, get_config


def _create_engine(db_config: DatabaseConfiguration) -> AsyncEngine:
    db_url = URL.create(
        drivername=db_config.drivername,
        username=db_config.username,
        password=db_config.password,
        host=db_config.host,
        port=db_config.port,
        database=db_config.database,
    )
    return create_async_engine(
        db_url,
        echo=db_config.echo,
        pool_recycle=3600,
    )


@functools.cache
def user_database() -> AsyncEngine:
    return _create_engine(get_config().openml_database)


@functools.cache
def expdb_database() -> AsyncEngine:
    return _create_engine(get_config().expdb_database)


async def close_databases() -> None:
    """Close all database connections."""
    if user_database.cache_info().currsize == 1:
        await user_database().dispose()
        user_database.cache_clear()
    if expdb_database.cache_info().currsize == 1:
        await expdb_database().dispose()
        expdb_database.cache_clear()
