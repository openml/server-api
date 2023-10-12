import os
from pathlib import Path

from config import _apply_defaults_to_subtables, load_database_configuration


def test_apply_defaults_to_subtables_applies_defaults() -> None:
    input_ = {"foo": {"defaults": {1: 1}, "other": {}}}
    expected = {"other": {1: 1}}
    output = _apply_defaults_to_subtables(input_, table="foo")
    assert expected == output


def test_apply_defaults_to_subtables_does_not_override() -> None:
    input_ = {"foo": {"defaults": {1: 1}, "other": {1: 2}}}
    expected = {"other": {1: 2}}
    output = _apply_defaults_to_subtables(input_, table="foo")
    assert expected == output


def test_load_configuration_adds_environment_variables(default_configuration_file: Path) -> None:
    database_configuration = load_database_configuration(default_configuration_file)
    assert database_configuration["openml"]["username"] == "root"

    load_database_configuration.cache_clear()
    os.environ["OPENML_DATABASES_OPENML_USERNAME"] = "foo"
    database_configuration = load_database_configuration(default_configuration_file)
    assert database_configuration["openml"]["username"] == "foo"
