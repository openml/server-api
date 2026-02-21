from __future__ import annotations

import io
import logging
import os
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from config import _load_configuration, _config_file

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

MINIO_ACCESS_KEY_ENV = "OPENML_MINIO_ACCESS_KEY"
MINIO_SECRET_KEY_ENV = "OPENML_MINIO_SECRET_KEY"  # noqa: S105


def _minio_config(file: Path = _config_file) -> dict[str, str]:
    cfg = _load_configuration(file).get("minio", {})
    return {
        "endpoint_url": cfg.get("endpoint_url", "http://minio:9000"),
        "bucket": cfg.get("bucket", "datasets"),
        "access_key": os.environ.get(MINIO_ACCESS_KEY_ENV, cfg.get("access_key", "minioadmin")),
        "secret_key": os.environ.get(MINIO_SECRET_KEY_ENV, cfg.get("secret_key", "minioadmin")),
    }


def _object_key(dataset_id: int) -> str:
    """Return the MinIO object key for a dataset, matching the existing URL pattern."""
    ten_thousands_prefix = f"{dataset_id // 10_000:04d}"
    padded_id = f"{dataset_id:04d}"
    return f"datasets/{ten_thousands_prefix}/{padded_id}/dataset_{dataset_id}.pq"


def upload_to_minio(file_bytes: bytes, dataset_id: int) -> str:
    """Upload *file_bytes* to MinIO and return the object key.

    Raises ``RuntimeError`` on upload failure so callers can convert to HTTP 500.
    """
    cfg = _minio_config()
    key = _object_key(dataset_id)
    try:
        client = boto3.client(
            "s3",
            endpoint_url=cfg["endpoint_url"],
            aws_access_key_id=cfg["access_key"],
            aws_secret_access_key=cfg["secret_key"],
        )
        client.upload_fileobj(io.BytesIO(file_bytes), cfg["bucket"], key)
        logger.info("Uploaded dataset %d to MinIO at key '%s'", dataset_id, key)
    except (BotoCoreError, ClientError) as exc:
        msg = f"Failed to upload dataset {dataset_id} to MinIO: {exc}"
        logger.exception(msg)
        raise RuntimeError(msg) from exc
    return key
