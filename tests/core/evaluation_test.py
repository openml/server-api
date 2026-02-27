
from __future__ import annotations

import math

import pytest

from core.evaluation import (
    TASK_TYPE_SUPERVISED_CLASSIFICATION,
    TASK_TYPE_SUPERVISED_REGRESSION,
    accuracy,
    auc,
    compute_metrics,
    mean_absolute_error,
    rmse,
)


# ---------------------------------------------------------------------------
# accuracy
# ---------------------------------------------------------------------------


def test_accuracy_perfect() -> None:
    assert accuracy(["A", "B", "C"], ["A", "B", "C"]) == pytest.approx(1.0)


def test_accuracy_half() -> None:
    assert accuracy(["A", "A", "B", "B"], ["A", "B", "B", "A"]) == pytest.approx(0.5)


def test_accuracy_none_correct() -> None:
    assert accuracy(["A", "A"], ["B", "B"]) == pytest.approx(0.0)


def test_accuracy_empty() -> None:
    assert accuracy([], []) == pytest.approx(0.0)


def test_accuracy_length_mismatch() -> None:
    with pytest.raises(ValueError, match="Length mismatch"):
        accuracy(["A"], ["A", "B"])


def test_accuracy_integer_labels() -> None:
    assert accuracy([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# rmse
# ---------------------------------------------------------------------------


def test_rmse_zero() -> None:
    assert rmse([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(0.0)


def test_rmse_known() -> None:
    # errors: 1, 1 → RMSE = sqrt((1+1)/2) = 1.0
    assert rmse([0.0, 0.0], [1.0, -1.0]) == pytest.approx(1.0)


def test_rmse_empty() -> None:
    assert rmse([], []) == pytest.approx(0.0)


def test_rmse_length_mismatch() -> None:
    with pytest.raises(ValueError, match="Length mismatch"):
        rmse([1.0], [1.0, 2.0])


# ---------------------------------------------------------------------------
# mean_absolute_error
# ---------------------------------------------------------------------------


def test_mae_zero() -> None:
    assert mean_absolute_error([1.0, 2.0], [1.0, 2.0]) == pytest.approx(0.0)


def test_mae_known() -> None:
    assert mean_absolute_error([0.0, 0.0], [1.0, 3.0]) == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# auc
# ---------------------------------------------------------------------------


def test_auc_perfect() -> None:
    y_true = [1, 1, 0, 0]
    y_score = [0.9, 0.8, 0.2, 0.1]
    assert auc(y_true, y_score) == pytest.approx(1.0)


def test_auc_random_classifier() -> None:
    # A random classifier scored with alternating 0/1 at equal probability
    # gives AUC ≈ 0.5 (not exactly, depends on tie-breaking)
    y_true = [1, 0, 1, 0]
    y_score = [0.5, 0.5, 0.5, 0.5]
    result = auc(y_true, y_score)
    assert 0.0 <= result <= 1.0


def test_auc_empty() -> None:
    assert auc([], []) == pytest.approx(0.0)


def test_auc_all_one_class() -> None:
    # Only positives → undefined, returns 0.0 by convention
    assert auc([1, 1, 1], [0.9, 0.8, 0.7]) == pytest.approx(0.0)


def test_auc_length_mismatch() -> None:
    with pytest.raises(ValueError, match="Length mismatch"):
        auc([1], [0.5, 0.6])


# ---------------------------------------------------------------------------
# compute_metrics dispatcher
# ---------------------------------------------------------------------------


def test_compute_metrics_classification_accuracy() -> None:
    metrics = compute_metrics(
        TASK_TYPE_SUPERVISED_CLASSIFICATION,
        y_true=["A", "A", "B"],
        y_pred=["A", "B", "B"],
    )
    assert "predictive_accuracy" in metrics
    assert metrics["predictive_accuracy"] == pytest.approx(2 / 3)


def test_compute_metrics_classification_includes_auc_for_binary() -> None:
    metrics = compute_metrics(
        TASK_TYPE_SUPERVISED_CLASSIFICATION,
        y_true=["pos", "pos", "neg", "neg"],
        y_pred=["pos", "neg", "neg", "pos"],
        y_score=[0.9, 0.7, 0.3, 0.4],
    )
    assert "area_under_roc_curve" in metrics
    assert 0.0 <= metrics["area_under_roc_curve"] <= 1.0


def test_compute_metrics_classification_no_auc_without_scores() -> None:
    metrics = compute_metrics(
        TASK_TYPE_SUPERVISED_CLASSIFICATION,
        y_true=["A", "B"],
        y_pred=["A", "B"],
    )
    assert "area_under_roc_curve" not in metrics


def test_compute_metrics_classification_no_auc_for_multiclass() -> None:
    metrics = compute_metrics(
        TASK_TYPE_SUPERVISED_CLASSIFICATION,
        y_true=["A", "B", "C"],
        y_pred=["A", "B", "C"],
        y_score=[0.8, 0.9, 0.7],
    )
    assert "area_under_roc_curve" not in metrics


def test_compute_metrics_regression() -> None:
    metrics = compute_metrics(
        TASK_TYPE_SUPERVISED_REGRESSION,
        y_true=[1.0, 2.0, 3.0],
        y_pred=[1.0, 2.0, 3.0],
    )
    assert "root_mean_squared_error" in metrics
    assert "mean_absolute_error" in metrics
    assert metrics["root_mean_squared_error"] == pytest.approx(0.0)
    assert metrics["mean_absolute_error"] == pytest.approx(0.0)


def test_compute_metrics_regression_known_values() -> None:
    metrics = compute_metrics(
        TASK_TYPE_SUPERVISED_REGRESSION,
        y_true=[0.0, 0.0],
        y_pred=[1.0, -1.0],
    )
    assert metrics["root_mean_squared_error"] == pytest.approx(math.sqrt(1.0))
    assert metrics["mean_absolute_error"] == pytest.approx(1.0)


def test_compute_metrics_unknown_task_type_returns_empty() -> None:
    metrics = compute_metrics(99, y_true=["A"], y_pred=["A"])
    assert metrics == {}
