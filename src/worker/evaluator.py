from __future__ import annotations

import csv
import io
import logging
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

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

# Shared default; also set in routers/openml/runs.py — kept in sync via config key
_DEFAULT_UPLOAD_DIR = "/tmp/openml_runs"  # noqa: S108


def _parse_predictions_arff(content: str) -> dict[str, list[Any]]:
    """Parse an OpenML predictions ARFF using csv.reader to handle quoted values.

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

        # Use csv.reader so quoted commas and quoted values are handled correctly
        try:
            (parts,) = csv.reader(io.StringIO(stripped))
        except (ValueError, StopIteration):
            continue
        parts = [p.strip().strip("'\"") for p in parts]

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


def _fetch_arff(url: str) -> str:
    """Download an ARFF from a URL, returning the decoded text content."""
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
        return cast("str", resp.read().decode("utf-8", errors="replace"))


def _parse_dataset_labels(
    content: str,
    target_attribute: str,
) -> dict[int, str]:
    """Parse a dataset ARFF and return a {row_index: label} map for target_attribute.

    Returns an empty dict (with a warning) when the target column is absent.
    """
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
            try:
                (row,) = csv.reader(io.StringIO(stripped))
                data_rows.append([v.strip().strip("'\"") for v in row])
            except (ValueError, StopIteration):
                continue

    if target_attribute not in attr_names:
        log.warning("Target attribute '%s' not found in dataset.", target_attribute)
        return {}

    target_idx = attr_names.index(target_attribute)
    return {i: row[target_idx] for i, row in enumerate(data_rows) if target_idx < len(row)}


def _evaluate_run(run_id: int, expdb: Connection) -> None:  # noqa: C901, PLR0911, PLR0912, PLR0915
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

    # Fetch dataset once (not per fold) and build a complete label map
    try:
        dataset_content = _fetch_arff(dataset_url)
    except Exception:
        log.exception("Failed to download dataset from %s", dataset_url)
        database.processing.mark_error(run_id, "could not fetch dataset", expdb)
        return
    label_map = _parse_dataset_labels(dataset_content, target_attr)
    if not label_map:
        database.processing.mark_error(run_id, "target attribute not found in dataset", expdb)
        return

    cfg = load_routing_configuration()
    task_id = run.task_id
    splits_url = f"{cfg.get('server_url', '')}api_splits/get/{task_id}/Task_{task_id}_splits.arff"
    try:
        splits_content = _fetch_arff(splits_url)
    except Exception:
        log.exception("Could not fetch splits for task %d", task_id)
        database.processing.mark_error(run_id, "could not fetch splits", expdb)
        return

    splits = parse_arff_splits(splits_content)

    upload_dir: str = load_configuration().get("upload_dir", _DEFAULT_UPLOAD_DIR)
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

    # Determine available repeats and iterate all of them
    all_repeats = sorted({int(e["repeat"]) for e in splits})

    all_true: list[str | int | float] = []
    all_pred: list[str | int | float] = []
    all_score: list[float] = []
    # has_scores starts True; disabled if any fold has a missing score
    has_scores = any(v is not None for v in conf_map.values())

    for repeat in all_repeats:
        fold_index = build_fold_index(splits, repeat=repeat)
        for _train_ids, test_ids in fold_index.values():
            # Validate ground truth: error out if any row ID is missing
            missing = [rid for rid in test_ids if rid not in label_map]
            if missing:
                database.processing.mark_error(
                    run_id,
                    f"ground-truth missing for row_ids {missing[:5]}",
                    expdb,
                )
                return

            y_true_fold = [label_map[rid] for rid in test_ids]
            y_pred_fold = [pred_map.get(rid, "") for rid in test_ids]
            all_true.extend(y_true_fold)
            all_pred.extend(y_pred_fold)

            if has_scores:
                fold_scores: list[float] = []
                for rid in test_ids:
                    raw = conf_map.get(rid)
                    if raw is None:
                        # Score missing for this fold — disable AUC for whole run
                        has_scores = False
                        fold_scores = []
                        break
                    fold_scores.append(float(raw))
                all_score.extend(fold_scores)

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
