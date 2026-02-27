from __future__ import annotations

import math
from collections.abc import Sequence


def accuracy(y_true: Sequence[str | int], y_pred: Sequence[str | int]) -> float:
    """Fraction of predictions that exactly match the ground truth."""
    if len(y_true) != len(y_pred):
        msg = f"Length mismatch: {len(y_true)} vs {len(y_pred)}"
        raise ValueError(msg)
    if not y_true:
        return 0.0
    correct = sum(t == p for t, p in zip(y_true, y_pred, strict=True))
    return correct / len(y_true)


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Root Mean Squared Error."""
    if len(y_true) != len(y_pred):
        msg = f"Length mismatch: {len(y_true)} vs {len(y_pred)}"
        raise ValueError(msg)
    if not y_true:
        return 0.0
    mse = sum((t - p) ** 2 for t, p in zip(y_true, y_pred, strict=True)) / len(y_true)
    return math.sqrt(mse)


def mean_absolute_error(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Mean Absolute Error."""
    if len(y_true) != len(y_pred):
        msg = f"Length mismatch: {len(y_true)} vs {len(y_pred)}"
        raise ValueError(msg)
    if not y_true:
        return 0.0
    return sum(abs(t - p) for t, p in zip(y_true, y_pred, strict=True)) / len(y_true)


def auc(y_true: Sequence[int], y_score: Sequence[float]) -> float:
    """Binary ROC AUC via an O(n log n) rank-based Mann-Whitney U statistic.

    Mathematically equivalent to the area under the ROC curve.

    y_true: sequence of 0/1 ground-truth labels.
    y_score: sequence of predicted probabilities for the positive class (label=1).

    Raises:
        ValueError: if y_true contains values outside {0, 1} or lengths differ.
    """
    if len(y_true) != len(y_score):
        msg = f"Length mismatch: {len(y_true)} vs {len(y_score)}"
        raise ValueError(msg)
    if not y_true:
        return 0.0

    unique = set(y_true)
    invalid = unique - {0, 1}
    if invalid:
        msg = f"y_true must contain only 0/1 labels; found {invalid}"
        raise ValueError(msg)

    n_pos = sum(y_true)
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.0

    # O(n log n): rank all scores, then use the rank-sum formula
    pairs = sorted(zip(y_score, y_true, strict=False), key=lambda x: x[0])

    n = len(pairs)
    ranks: list[float] = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and pairs[j][0] == pairs[j + 1][0]:
            j += 1
        mid_rank = (i + j) / 2 + 1  # 1-indexed
        for k in range(i, j + 1):
            ranks[k] = mid_rank
        i = j + 1

    rank_sum_pos = sum(ranks[k] for k in range(n) if pairs[k][1] == 1)
    u_pos = rank_sum_pos - n_pos * (n_pos + 1) / 2
    return u_pos / (n_pos * n_neg)


#: Task type IDs from the OpenML schema
TASK_TYPE_SUPERVISED_CLASSIFICATION = 1
TASK_TYPE_SUPERVISED_REGRESSION = 2


def compute_metrics(
    task_type_id: int,
    y_true: Sequence[str | int | float],
    y_pred: Sequence[str | int | float],
    y_score: Sequence[float] | None = None,
) -> dict[str, float]:
    """Compute all applicable metrics for the given task type.

    Returns a dict of {measure_name: value} using the same names found in
    the OpenML `math_function` table (e.g. 'predictive_accuracy',
    'area_under_roc_curve').
    """
    results: dict[str, float] = {}

    if task_type_id == TASK_TYPE_SUPERVISED_CLASSIFICATION:
        str_true = [str(v) for v in y_true]
        str_pred = [str(v) for v in y_pred]
        results["predictive_accuracy"] = accuracy(str_true, str_pred)

        # AUC only when binary and scores are provided
        unique_labels = set(str_true)
        if y_score is not None and len(unique_labels) == 2:  # noqa: PLR2004
            # Map the positive class (lexicographically larger, matching OpenML)
            pos_label = max(unique_labels)
            int_true = [1 if str(v) == pos_label else 0 for v in y_true]
            results["area_under_roc_curve"] = auc(int_true, list(y_score))

    elif task_type_id == TASK_TYPE_SUPERVISED_REGRESSION:
        float_true = [float(v) for v in y_true]
        float_pred = [float(v) for v in y_pred]
        results["root_mean_squared_error"] = rmse(float_true, float_pred)
        results["mean_absolute_error"] = mean_absolute_error(float_true, float_pred)

    return results
