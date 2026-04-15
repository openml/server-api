import asyncio
from http import HTTPStatus

import httpx


async def test_evaluationmeasure_list(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/evaluationmeasure/list")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == [
        "area_under_roc_curve",
        "average_cost",
        "binominal_test",
        "build_cpu_time",
        "build_memory",
        "c_index",
        "chi-squared",
        "class_complexity",
        "class_complexity_gain",
        "confusion_matrix",
        "correlation_coefficient",
        "cortana_quality",
        "coverage",
        "f_measure",
        "information_gain",
        "jaccard",
        "kappa",
        "kb_relative_information_score",
        "kohavi_wolpert_bias_squared",
        "kohavi_wolpert_error",
        "kohavi_wolpert_sigma_squared",
        "kohavi_wolpert_variance",
        "kononenko_bratko_information_score",
        "matthews_correlation_coefficient",
        "mean_absolute_error",
        "mean_class_complexity",
        "mean_class_complexity_gain",
        "mean_f_measure",
        "mean_kononenko_bratko_information_score",
        "mean_precision",
        "mean_prior_absolute_error",
        "mean_prior_class_complexity",
        "mean_recall",
        "mean_weighted_area_under_roc_curve",
        "mean_weighted_f_measure",
        "mean_weighted_precision",
        "weighted_recall",
        "number_of_instances",
        "os_information",
        "positives",
        "precision",
        "predictive_accuracy",
        "prior_class_complexity",
        "prior_entropy",
        "probability",
        "quality",
        "ram_hours",
        "recall",
        "relative_absolute_error",
        "root_mean_prior_squared_error",
        "root_mean_squared_error",
        "root_relative_squared_error",
        "run_cpu_time",
        "run_memory",
        "run_virtual_memory",
        "scimark_benchmark",
        "single_point_area_under_roc_curve",
        "total_cost",
        "unclassified_instance_count",
        "usercpu_time_millis",
        "usercpu_time_millis_testing",
        "usercpu_time_millis_training",
        "webb_bias",
        "webb_error",
        "webb_variance",
        "joint_entropy",
        "pattern_team_auroc10",
        "wall_clock_time_millis",
        "wall_clock_time_millis_training",
        "wall_clock_time_millis_testing",
        "unweighted_recall",
    ]


# -- migration test --


async def test_evaluationmeasure_list_migration(
    py_api: httpx.AsyncClient, php_api: httpx.AsyncClient
) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get("/evaluationmeasure/list"),
        php_api.get("/evaluationmeasure/list"),
    )
    assert py_response.status_code == php_response.status_code
    assert py_response.json() == php_response.json()["evaluation_measures"]["measures"]["measure"]
