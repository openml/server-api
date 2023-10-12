from __future__ import annotations

import os
import tomllib
import typing
from pathlib import Path

from dotenv import load_dotenv

TomlTable = dict[str, typing.Any]


def apply_defaults_to_subtables(configuration: TomlTable, table: str) -> TomlTable:
    defaults = configuration[table]["defaults"]
    return {
        subtable: defaults | overrides
        for subtable, overrides in configuration[table].items()
        if subtable != "defaults"
    }


def load_configuration(file: Path) -> TomlTable:
    configuration = tomllib.loads(file.read_text())
    configuration["databases"] = apply_defaults_to_subtables(
        configuration,
        table="databases",
    )
    return configuration


load_dotenv()
_configuration = load_configuration(Path(__file__).parent / "config.toml")

DATABASE_CONFIGURATION = _configuration["databases"]
DATABASE_CONFIGURATION["openml"]["username"] = os.environ.get(
    "OPENML_DATABASES_OPENML_USERNAME",
    "root",
)
DATABASE_CONFIGURATION["openml"]["password"] = os.environ.get(
    "OPENML_DATABASES_OPENML_PASSWORD",
    "ok",
)
DATABASE_CONFIGURATION["expdb"]["username"] = os.environ.get(
    "OPENML_DATABASES_EXPDB_USERNAME",
    "root",
)
DATABASE_CONFIGURATION["expdb"]["password"] = os.environ.get(
    "OPENML_DATABASES_EXPDB_PASSWORD",
    "ok",
)
