from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from main import app


@pytest.fixture()
def api_client() -> Generator[FastAPI, None, None]:
    return TestClient(app)
