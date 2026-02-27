from __future__ import annotations

import logging
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

import database.processing
import database.runs
import database.tasks
from config import load_configuration, load_routing_configuration
from core.evaluation import compute_metrics
from core.formatting import _format_dataset_url
from core.splits import build_fold_index, parse_arff_splits
from database.datasets import get as get_dataset

if TYPE_CHECKING:
    from sqlalchemy import Connection

log = logging.getLogger(__name__)


def _parse_predictions_arff(content: str) -> dict[str, list[Any]]:
    """Parse an OpenML predictions ARFF.

    Returns a dict with keys: 'row_id', 'prediction', 'confidence' (optional).
    Expected columns: row_id, fold, repeat, prediction [, confidence.*]
    """
    result: dict[str, list[Any]] = {"row_id": [], "prediction": [], "confidence": []}
    in_data = False

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        if stripped.upper().startswith("@DATA"):
            in_data = True
            continue
        if not in_data:
            continue

        parts = [p.strip().strip("'\"") for p in stripped.split(",")]
        if not parts:
            continue
        try:
            row_id = int(parts[0])
            prediction = parts[3] if len(parts) > 3 else parts[-1]  # noqa: PLR2004
            confidence = float(parts[4]) if len(parts) > 4 else None  # noqa: PLR2004
        except (ValueError, IndexError):
            continue

        result["row_id"].append(row_id)
        result["prediction"].append(prediction)
        result["confidence"].append(confidence)

    return result


def _load_ground_truth(
    dataset_url: str,
    target_attribute: str,
    test_row_ids: list[int],
) -> list[str]:
    """Download the dataset ARFF and extract the target column for given row IDs.

    Only extracts rows whose 0-based index is in `test_row_ids`.
    Returns labels as strings in the order of `test_row_ids`.
    """
    try:
        with urllib.request.urlopen(dataset_url, timeout=30) as resp:  # noqa: S310
            content = resp.read().decode("utf-8", errors="replace")
    except Exception:
        log.exception("Failed to download dataset from %s", dataset_url)
        return []

    attr_names: list[str] = []
    data_rows: list[list[str]] = []
    in_data = False

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        if stripped.upper().startswith("@ATTRIBUTE"):
            parts = stripped.split(None, 2)
            attr_names.append(parts[1].strip("'\"") if len(parts) >= 2 else "")  # noqa: PLR2004
            continue
        if stripped.upper().startswith("@DATA"):
            in_data = True
            continue
        if in_data:
            data_rows.append([v.strip().strip("'\"") for v in stripped.split(",")])

    if target_attribute not in attr_names:
        log.warning("Target attribute '%s' not found in dataset.", target_attribute)
        return []

    target_idx = attr_names.index(target_attribute)
    pos_to_label = {
        i: row[target_idx]
        for i, row in enumerate(data_rows)
        if i in set(test_row_ids) and target_idx < len(row)
    }
    return [pos_to_label.get(rid, "") for rid in test_row_ids]


def _evaluate_run(run_id: int, expdb: Connection) -> None:  # noqa: C901, PLR0911, PLR0915
    """Evaluate a single run, store metrics, mark processing entry done/error."""
    run = database.runs.get(run_id, expdb)
    if run is None:
        log.warning("Run %d not found; skipping.", run_id)
        database.processing.mark_error(run_id, "run row not found", expdb)
        return

    task_row = database.tasks.get(run.task_id, expdb)
    if task_row is None:
        database.processing.mark_error(run_id, "task not found", expdb)
        return

    task_type_row = database.tasks.get_task_type(task_row.ttid, expdb)
    if task_type_row is None:
        database.processing.mark_error(run_id, "task type not found", expdb)
        return

    task_inputs = {
        row.input: int(row.value) if str(row.value).isdigit() else row.value
        for row in database.tasks.get_input_for_task(run.task_id, expdb)
    }

    dataset_id = task_inputs.get("source_data")
    target_attr = str(task_inputs.get("target_feature", "class"))
    if not isinstance(dataset_id, int):
        database.processing.mark_error(run_id, "no source_data task input", expdb)
        return

    dataset_row = get_dataset(dataset_id, expdb)
    if dataset_row is None:
        database.processing.mark_error(run_id, "dataset not found", expdb)
        return
    dataset_url = str(_format_dataset_url(dataset_row))

    cfg = load_routing_configuration()
    task_id = run.task_id
    splits_url = f"{cfg.get('server_url', '')}api_splits/get/{task_id}/Task_{task_id}_splits.arff"
    try:
        with urllib.request.urlopen(splits_url, timeout=30) as resp:  # noqa: S310
            splits_content = resp.read().decode("utf-8", errors="replace")
    except Exception:
        log.exception("Could not fetch splits for task %d", task_id)
        database.processing.mark_error(run_id, "could not fetch splits", expdb)
        return

    fold_index = build_fold_index(parse_arff_splits(splits_content), repeat=0)

    upload_dir: str = load_configuration().get("upload_dir", "/tmp/openml_runs")  # noqa: S108
    predictions_path = Path(upload_dir) / str(run_id) / "predictions.arff"
    try:
        with predictions_path.open(encoding="utf-8") as fh:
            predictions_content = fh.read()
    except OSError:
        log.exception("Could not read predictions file for run %d", run_id)
        database.processing.mark_error(run_id, "predictions file not found", expdb)
        return

    predictions = _parse_predictions_arff(predictions_content)
    pred_map: dict[int, str] = dict(
        zip(predictions["row_id"], predictions["prediction"], strict=True),
    )
    conf_map: dict[int, float | None] = dict(
        zip(predictions["row_id"], predictions["confidence"], strict=True),
    )
    has_scores = any(v is not None for v in conf_map.values())

    all_true: list[str] = []
    all_pred: list[str] = []
    all_score: list[float] = []
    for train_ids, test_ids in fold_index.values():  # noqa: B007
        all_true.extend(_load_ground_truth(dataset_url, target_attr, test_ids))
        all_pred.extend(pred_map.get(rid, "") for rid in test_ids)
        if has_scores:
            for rid in test_ids:
                raw = conf_map.get(rid)
                all_score.append(float(raw) if raw is not None else 0.0)

    metrics = compute_metrics(
        task_type_id=task_row.ttid,
        y_true=all_true,
        y_pred=all_pred,
        y_score=all_score if has_scores else None,
    )
    for measure_name, value in metrics.items():
        database.runs.store_evaluation(
            run_id=run_id,
            function=measure_name,
            value=value,
            expdb=expdb,
        )

    database.processing.mark_done(run_id, expdb)
    log.info("Run %d evaluated: %s", run_id, metrics)


def process_pending_runs(expdb: Connection) -> None:
    """Consume all pending processing_run entries and evaluate each one.

    Designed to be called from a cron job or a management CLI command.
    Each run is evaluated independently; an error in one does not halt the rest.
    """
    pending = database.processing.get_pending(expdb)
    log.info("Processing %d pending run(s).", len(pending))
    for entry in pending:
        run_id = int(entry.run_id)
        try:
            _evaluate_run(run_id, expdb)
        except Exception:
            log.exception("Unexpected error evaluating run %d", run_id)
            database.processing.mark_error(run_id, "unexpected error", expdb)
