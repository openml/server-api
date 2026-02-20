import functools
import logging
import os
import tomllib
import typing
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TomlTable = dict[str, typing.Any]

CONFIG_DIRECTORY_ENV = "OPENML_REST_API_CONFIG_DIRECTORY"
CONFIG_FILE_ENV = "OPENML_REST_API_CONFIG_FILE"
DOTENV_FILE_ENV = "OPENML_REST_API_DOTENV_FILE"

OPENML_DB_USERNAME_ENV = "OPENML_DATABASES_OPENML_USERNAME"
OPENML_DB_PASSWORD_ENV = "OPENML_DATABASES_OPENML_PASSWORD"  # noqa: S105  # not a password
EXPDB_DB_USERNAME_ENV = "OPENML_DATABASES_EXPDB_USERNAME"
EXPDB_DB_PASSWORD_ENV = "OPENML_DATABASES_EXPDB_PASSWORD"  # noqa: S105  # not a password

_config_directory = Path(os.getenv(CONFIG_DIRECTORY_ENV, Path(__file__).parent))
_config_directory = _config_directory.expanduser().absolute()
_config_file = Path(os.getenv(CONFIG_FILE_ENV, _config_directory / "config.toml"))
_config_file = _config_file.expanduser().absolute()
_dotenv_file = Path(os.getenv(DOTENV_FILE_ENV, _config_directory / ".env"))
_dotenv_file = _dotenv_file.expanduser().absolute()

logger.info("Configuration directory is '%s'", _config_directory)
logger.info("Loading configuration file from '%s'", _config_file)
logger.info("Loading environment variables from '%s'", _dotenv_file)

load_dotenv(dotenv_path=_dotenv_file)


def _apply_defaults_to_siblings(configuration: TomlTable) -> TomlTable:
    defaults = configuration["defaults"]
    return {
        subtable: (defaults | overrides) if isinstance(overrides, dict) else overrides
        for subtable, overrides in configuration.items()
        if subtable != "defaults"
    }


@functools.cache
def _load_configuration(file: Path) -> TomlTable:
    return tomllib.loads(file.read_text())


def load_routing_configuration(file: Path = _config_file) -> TomlTable:
    return typing.cast("TomlTable", _load_configuration(file)["routing"])


@functools.cache
def load_database_configuration(file: Path = _config_file) -> TomlTable:
    configuration = _load_configuration(file)
    database_configuration = _apply_defaults_to_siblings(
        configuration["databases"],
    )
    database_configuration["openml"]["username"] = os.environ.get(
        OPENML_DB_USERNAME_ENV,
        "root",
    )
    database_configuration["openml"]["password"] = os.environ.get(
        OPENML_DB_PASSWORD_ENV,
        "ok",
    )
    database_configuration["expdb"]["username"] = os.environ.get(
        EXPDB_DB_USERNAME_ENV,
        "root",
    )
    database_configuration["expdb"]["password"] = os.environ.get(
        EXPDB_DB_PASSWORD_ENV,
        "ok",
    )
    return database_configuration


def load_configuration(file: Path = _config_file) -> TomlTable:
    return tomllib.loads(file.read_text())
