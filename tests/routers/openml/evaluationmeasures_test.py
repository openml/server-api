from http import HTTPStatus

from starlette.testclient import TestClient


def test_evaluationmeasure_list(py_api: TestClient) -> None:
    response = py_api.get("/evaluationmeasure/list")
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


def test_estimation_procedure_list(py_api: TestClient) -> None:
    response = py_api.get("/estimationprocedure/list")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == [
        {
            "id": 1,
            "task_type_id": 1,
            "name": "10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 2,
            "task_type_id": 1,
            "name": "5 times 2-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 5,
            "folds": 2,
            "stratified_sampling": True,
        },
        {
            "id": 3,
            "task_type_id": 1,
            "name": "10 times 10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 10,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 4,
            "task_type_id": 1,
            "name": "Leave one out",
            "type": "leaveoneout",
            "repeats": 1,
            "stratified_sampling": False,
        },
        {
            "id": 5,
            "task_type_id": 1,
            "name": "10% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": True,
        },
        {
            "id": 6,
            "task_type_id": 1,
            "name": "33% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": True,
        },
        {
            "id": 7,
            "task_type_id": 2,
            "name": "10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": False,
        },
        {
            "id": 8,
            "task_type_id": 2,
            "name": "5 times 2-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 5,
            "folds": 2,
            "stratified_sampling": False,
        },
        {
            "id": 9,
            "task_type_id": 2,
            "name": "10 times 10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 10,
            "folds": 10,
            "stratified_sampling": False,
        },
        {
            "id": 10,
            "task_type_id": 2,
            "name": "Leave one out",
            "type": "leaveoneout",
            "repeats": 1,
            "stratified_sampling": False,
        },
        {
            "id": 11,
            "task_type_id": 2,
            "name": "10% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": False,
        },
        {
            "id": 12,
            "task_type_id": 2,
            "name": "33% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": False,
        },
        {
            "id": 13,
            "task_type_id": 3,
            "name": "10-fold Learning Curve",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 14,
            "task_type_id": 3,
            "name": "10 times 10-fold Learning Curve",
            "type": "crossvalidation",
            "repeats": 10,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 15,
            "task_type_id": 4,
            "name": "Interleaved Test then Train",
            "type": "testthentrain",
        },
        {
            "id": 16,
            "task_type_id": 1,
            "name": "Custom Holdout",
            "type": "customholdout",
            "repeats": 1,
            "folds": 1,
            "stratified_sampling": False,
        },
        {
            "id": 17,
            "task_type_id": 5,
            "name": "50 times Clustering",
            "type": "testontrainingdata",
            "repeats": 50,
        },
        {
            "id": 18,
            "task_type_id": 6,
            "name": "Holdout unlabeled",
            "type": "holdoutunlabeled",
            "repeats": 1,
            "folds": 1,
            "stratified_sampling": False,
        },
        {
            "id": 19,
            "task_type_id": 7,
            "name": "10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 20,
            "task_type_id": 7,
            "name": "5 times 2-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 5,
            "folds": 2,
            "stratified_sampling": True,
        },
        {
            "id": 21,
            "task_type_id": 7,
            "name": "10 times 10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 10,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 22,
            "task_type_id": 7,
            "name": "Leave one out",
            "type": "leaveoneout",
            "repeats": 1,
            "stratified_sampling": False,
        },
        {
            "id": 23,
            "task_type_id": 1,
            "name": "100 times 10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 100,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 24,
            "task_type_id": 2,
            "name": "Custom 10-fold Crossvalidation",
            "type": "customholdout",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": False,
        },
        {
            "id": 25,
            "task_type_id": 1,
            "name": "4-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 4,
            "stratified_sampling": True,
        },
        {
            "id": 26,
            "task_type_id": 1,
            "name": "Test on Training Data",
            "type": "testontrainingdata",
        },
        {
            "id": 27,
            "task_type_id": 2,
            "name": "Test on Training Data",
            "type": "testontrainingdata",
        },
        {
            "id": 28,
            "task_type_id": 1,
            "name": "20% Holdout (Ordered)",
            "type": "holdout_ordered",
            "repeats": 1,
            "folds": 1,
            "percentage": 20,
        },
        {
            "id": 29,
            "task_type_id": 9,
            "name": "10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 30,
            "task_type_id": 10,
            "name": "10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 31,
            "task_type_id": 10,
            "name": "5 times 2-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 5,
            "folds": 2,
            "stratified_sampling": True,
        },
        {
            "id": 32,
            "task_type_id": 10,
            "name": "10 times 10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 10,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 33,
            "task_type_id": 10,
            "name": "10% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": True,
        },
        {
            "id": 34,
            "task_type_id": 10,
            "name": "33% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": True,
        },
        {
            "id": 35,
            "task_type_id": 11,
            "name": "33% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": True,
        },
    ]
