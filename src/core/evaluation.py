from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Individual metrics
# ---------------------------------------------------------------------------


def accuracy(y_true: list[str | int], y_pred: list[str | int]) -> float:
    """Fraction of predictions that exactly match the ground truth."""
    if len(y_true) != len(y_pred):
        msg = f"Length mismatch: {len(y_true)} vs {len(y_pred)}"
        raise ValueError(msg)
    if not y_true:
        return 0.0
    correct = sum(t == p for t, p in zip(y_true, y_pred, strict=True))
    return correct / len(y_true)


def rmse(y_true: list[float], y_pred: list[float]) -> float:
    """Root Mean Squared Error."""
    if len(y_true) != len(y_pred):
        msg = f"Length mismatch: {len(y_true)} vs {len(y_pred)}"
        raise ValueError(msg)
    if not y_true:
        return 0.0
    mse = sum((t - p) ** 2 for t, p in zip(y_true, y_pred, strict=True)) / len(y_true)
    return math.sqrt(mse)


def mean_absolute_error(y_true: list[float], y_pred: list[float]) -> float:
    """Mean Absolute Error."""
    if len(y_true) != len(y_pred):
        msg = f"Length mismatch: {len(y_true)} vs {len(y_pred)}"
        raise ValueError(msg)
    if not y_true:
        return 0.0
    return sum(abs(t - p) for t, p in zip(y_true, y_pred, strict=True)) / len(y_true)


def auc(y_true: list[int], y_score: list[float]) -> float:
    """Binary ROC AUC via the Wilcoxon-Mann-Whitney U statistic.

    Mathematically equivalent to the area under the ROC curve.
    Counts concordant pairs: for each (positive, negative) pair, score 1 if
    y_score[pos] > y_score[neg], 0.5 if tied, 0 otherwise, then normalise.

    y_true: list of 0/1 ground-truth labels.
    y_score: list of predicted probabilities for the positive class (label=1).
    """
    if len(y_true) != len(y_score):
        msg = f"Length mismatch: {len(y_true)} vs {len(y_score)}"
        raise ValueError(msg)
    if not y_true:
        return 0.0

    n_pos = sum(y_true)
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.0

    pos_scores = [s for t, s in zip(y_true, y_score, strict=True) if t == 1]
    neg_scores = [s for t, s in zip(y_true, y_score, strict=True) if t == 0]

    concordant = 0.0
    for ps in pos_scores:
        for ns in neg_scores:
            if ps > ns:
                concordant += 1.0
            elif ps == ns:
                concordant += 0.5

    return concordant / (n_pos * n_neg)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

#: Task type IDs from the OpenML schema
TASK_TYPE_SUPERVISED_CLASSIFICATION = 1
TASK_TYPE_SUPERVISED_REGRESSION = 2


def compute_metrics(
    task_type_id: int,
    y_true: list[str | int | float],
    y_pred: list[str | int | float],
    y_score: list[float] | None = None,
) -> dict[str, float]:
    """Compute all applicable metrics for the given task type.

    Returns a dict of {measure_name: value} using the same names found in
    the OpenML `math_function` table (e.g. 'predictive_accuracy', 'area_under_roc_curve').
    """
    results: dict[str, float] = {}

    if task_type_id == TASK_TYPE_SUPERVISED_CLASSIFICATION:
        str_true = [str(v) for v in y_true]
        str_pred = [str(v) for v in y_pred]
        results["predictive_accuracy"] = accuracy(str_true, str_pred)

        # AUC only when binary and scores are provided
        unique_labels = set(str_true)
        if y_score is not None and len(unique_labels) == 2:  # noqa: PLR2004
            # Map the positive class (lexicographically larger, matching OpenML convention)
            pos_label = max(unique_labels)
            int_true = [1 if str(v) == pos_label else 0 for v in y_true]
            results["area_under_roc_curve"] = auc(int_true, y_score)

    elif task_type_id == TASK_TYPE_SUPERVISED_REGRESSION:
        float_true = [float(v) for v in y_true]
        float_pred = [float(v) for v in y_pred]
        results["root_mean_squared_error"] = rmse(float_true, float_pred)
        results["mean_absolute_error"] = mean_absolute_error(float_true, float_pred)

    return results
