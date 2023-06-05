import json
import pathlib
from typing import Any, Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from main import app


@pytest.fixture()
def api_client() -> Generator[FastAPI, None, None]:
    return TestClient(app)


@pytest.fixture()
def dataset_130() -> Generator[dict[str, Any], None, None]:
    json_path = (
        pathlib.Path(__file__).parent / "resources" / "datasets" / "dataset_130.json"
    )
    with json_path.open("r") as dataset_file:
        yield json.load(dataset_file)
