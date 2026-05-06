import os
from pathlib import Path
from unittest import mock

from config import load_database_configuration


def test_load_configuration_adds_environment_variables(default_configuration_file: Path) -> None:
    database_configuration = load_database_configuration(default_configuration_file)
    assert database_configuration["openml"].username == "root"

    load_database_configuration.cache_clear()
    with mock.patch.dict(os.environ, {"OPENML_DATABASES_OPENML_USERNAME": "foo"}):
        database_configuration = load_database_configuration(default_configuration_file)
    assert database_configuration["openml"].username == "foo"
