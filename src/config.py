import functools
import os
import tomllib
import typing
from pathlib import Path

from dotenv import load_dotenv

TomlTable = dict[str, typing.Any]


def _apply_defaults_to_siblings(configuration: TomlTable) -> TomlTable:
    defaults = configuration["defaults"]
    return {
        subtable: (defaults | overrides) if isinstance(overrides, dict) else overrides
        for subtable, overrides in configuration.items()
        if subtable != "defaults"
    }


@functools.cache
def load_database_configuration(file: Path = Path(__file__).parent / "config.toml") -> TomlTable:
    configuration = tomllib.loads(file.read_text())

    database_configuration = _apply_defaults_to_siblings(
        configuration["databases"],
    )
    load_dotenv()
    database_configuration["openml"]["username"] = os.environ.get(
        "OPENML_DATABASES_OPENML_USERNAME",
        "root",
    )
    database_configuration["openml"]["password"] = os.environ.get(
        "OPENML_DATABASES_OPENML_PASSWORD",
        "ok",
    )
    database_configuration["expdb"]["username"] = os.environ.get(
        "OPENML_DATABASES_EXPDB_USERNAME",
        "root",
    )
    database_configuration["expdb"]["password"] = os.environ.get(
        "OPENML_DATABASES_EXPDB_PASSWORD",
        "ok",
    )
    return database_configuration


def load_configuration(file: Path = Path(__file__).parent / "config.toml") -> TomlTable:
    return tomllib.loads(file.read_text())
