from config import load_database_configuration
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.engine import URL

_user_engine = None
_expdb_engine = None


def _create_engine(database_name: str) -> Engine:
    database_configuration = load_database_configuration()
    db_url = URL.create(**database_configuration[database_name])
    return create_engine(
        db_url,
        echo=True,
        pool_recycle=3600,
    )


def user_database() -> Engine:
    global _user_engine
    if _user_engine is None:
        _user_engine = _create_engine("openml")
    with _user_engine.connect() as connection:
        yield connection


def expdb_database() -> Connection:
    global _expdb_engine
    if _expdb_engine is None:
        _expdb_engine = _create_engine("expdb")
    with _expdb_engine.connect() as connection:
        yield connection
