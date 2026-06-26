import functools

from loguru import logger
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.ext.declarative import DeferredReflection
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import DatabaseConfiguration, get_config


class Base(DeclarativeBase):
    pass


class ExpDBReflected(DeferredReflection):
    __abstract__ = True


class UserDBReflected(DeferredReflection):
    __abstract__ = True


class UserR(UserDBReflected, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)


class TaskTag(ExpDBReflected, Base):
    __tablename__ = "task_tag"


def _create_engine(db_config: DatabaseConfiguration) -> AsyncEngine:
    db_url = URL.create(
        drivername=db_config.drivername,
        username=db_config.username,
        password=db_config.password,
        host=db_config.host,
        port=db_config.port,
        database=db_config.database,
    )

    logger.info("Creating database engine for {db_url}", db_url=db_url)
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


async def reflect_db_schemas() -> None:
    async with user_database().connect() as connection:
        await connection.run_sync(UserDBReflected.prepare)  # type: ignore[arg-type]  # run_sync expects positional-only arg but `prepare` does not have it.
    async with expdb_database().connect() as connection:
        await connection.run_sync(ExpDBReflected.prepare)  # type: ignore[arg-type]  # as above.


async def close_databases() -> None:
    """Close all database connections."""
    for db in (user_database, expdb_database):
        if db.cache_info().currsize == 1:
            engine = db()
            logger.info("Disposing of engine connected to {db_url}", db_url=engine.url)
            try:
                await engine.dispose()
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Issue disposing of database engine for {db_url}",
                    db_url=engine.url,
                )
            db.cache_clear()
