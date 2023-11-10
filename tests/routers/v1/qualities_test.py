import http.client

import httpx
import pytest
from sqlalchemy import Connection, text
from starlette.testclient import TestClient


def _remove_quality_from_database(quality_name: str, expdb_test: Connection) -> None:
    expdb_test.execute(
        text(
            """
        DELETE FROM data_quality
        WHERE `quality`=:deleted_quality
        """,
        ),
        parameters={"deleted_quality": quality_name},
    )
    expdb_test.execute(
        text(
            """
        DELETE FROM quality
        WHERE `name`=:deleted_quality
        """,
        ),
        parameters={"deleted_quality": quality_name},
    )


@pytest.mark.php()
def test_list_qualities_identical(api_client: TestClient) -> None:
    original = httpx.get("http://server-api-php-api-1:80/api/v1/json/data/qualities/list")
    new = api_client.get("/v1/datasets/qualities/list")
    assert original.status_code == new.status_code
    assert original.json() == new.json()
    # To keep the test idempotent, we cannot test if reaction to database changes is identical


def test_list_qualities(api_client: TestClient, expdb_test: Connection) -> None:
    response = api_client.get("/v1/datasets/qualities/list")
    assert response.status_code == http.client.OK
    expected = {
        "data_qualities_list": {
            "quality": [
                "AutoCorrelation",
                "CfsSubsetEval_DecisionStumpAUC",
                "CfsSubsetEval_DecisionStumpErrRate",
                "CfsSubsetEval_DecisionStumpKappa",
                "CfsSubsetEval_NaiveBayesAUC",
                "CfsSubsetEval_NaiveBayesErrRate",
                "CfsSubsetEval_NaiveBayesKappa",
                "CfsSubsetEval_kNN1NAUC",
                "CfsSubsetEval_kNN1NErrRate",
                "CfsSubsetEval_kNN1NKappa",
                "ClassEntropy",
                "DecisionStumpAUC",
                "DecisionStumpErrRate",
                "DecisionStumpKappa",
                "Dimensionality",
                "EquivalentNumberOfAtts",
                "J48.00001.AUC",
                "J48.00001.ErrRate",
                "J48.00001.Kappa",
                "J48.0001.AUC",
                "J48.0001.ErrRate",
                "J48.0001.Kappa",
                "J48.001.AUC",
                "J48.001.ErrRate",
                "J48.001.Kappa",
                "MajorityClassPercentage",
                "MajorityClassSize",
                "MaxAttributeEntropy",
                "MaxKurtosisOfNumericAtts",
                "MaxMeansOfNumericAtts",
                "MaxMutualInformation",
                "MaxNominalAttDistinctValues",
                "MaxSkewnessOfNumericAtts",
                "MaxStdDevOfNumericAtts",
                "MeanAttributeEntropy",
                "MeanKurtosisOfNumericAtts",
                "MeanMeansOfNumericAtts",
                "MeanMutualInformation",
                "MeanNoiseToSignalRatio",
                "MeanNominalAttDistinctValues",
                "MeanSkewnessOfNumericAtts",
                "MeanStdDevOfNumericAtts",
                "MinAttributeEntropy",
                "MinKurtosisOfNumericAtts",
                "MinMeansOfNumericAtts",
                "MinMutualInformation",
                "MinNominalAttDistinctValues",
                "MinSkewnessOfNumericAtts",
                "MinStdDevOfNumericAtts",
                "MinorityClassPercentage",
                "MinorityClassSize",
                "NaiveBayesAUC",
                "NaiveBayesErrRate",
                "NaiveBayesKappa",
                "NumberOfBinaryFeatures",
                "NumberOfClasses",
                "NumberOfFeatures",
                "NumberOfInstances",
                "NumberOfInstancesWithMissingValues",
                "NumberOfMissingValues",
                "NumberOfNumericFeatures",
                "NumberOfSymbolicFeatures",
                "PercentageOfBinaryFeatures",
                "PercentageOfInstancesWithMissingValues",
                "PercentageOfMissingValues",
                "PercentageOfNumericFeatures",
                "PercentageOfSymbolicFeatures",
                "Quartile1AttributeEntropy",
                "Quartile1KurtosisOfNumericAtts",
                "Quartile1MeansOfNumericAtts",
                "Quartile1MutualInformation",
                "Quartile1SkewnessOfNumericAtts",
                "Quartile1StdDevOfNumericAtts",
                "Quartile2AttributeEntropy",
                "Quartile2KurtosisOfNumericAtts",
                "Quartile2MeansOfNumericAtts",
                "Quartile2MutualInformation",
                "Quartile2SkewnessOfNumericAtts",
                "Quartile2StdDevOfNumericAtts",
                "Quartile3AttributeEntropy",
                "Quartile3KurtosisOfNumericAtts",
                "Quartile3MeansOfNumericAtts",
                "Quartile3MutualInformation",
                "Quartile3SkewnessOfNumericAtts",
                "Quartile3StdDevOfNumericAtts",
                "REPTreeDepth1AUC",
                "REPTreeDepth1ErrRate",
                "REPTreeDepth1Kappa",
                "REPTreeDepth2AUC",
                "REPTreeDepth2ErrRate",
                "REPTreeDepth2Kappa",
                "REPTreeDepth3AUC",
                "REPTreeDepth3ErrRate",
                "REPTreeDepth3Kappa",
                "RandomTreeDepth1AUC",
                "RandomTreeDepth1ErrRate",
                "RandomTreeDepth1Kappa",
                "RandomTreeDepth2AUC",
                "RandomTreeDepth2ErrRate",
                "RandomTreeDepth2Kappa",
                "RandomTreeDepth3AUC",
                "RandomTreeDepth3ErrRate",
                "RandomTreeDepth3Kappa",
                "StdvNominalAttDistinctValues",
                "kNN1NAUC",
                "kNN1NErrRate",
                "kNN1NKappa",
            ],
        },
    }
    assert expected == response.json()

    deleted = expected["data_qualities_list"]["quality"].pop()
    _remove_quality_from_database(quality_name=deleted, expdb_test=expdb_test)

    response = api_client.get("/v1/datasets/qualities/list")
    assert response.status_code == http.client.OK
    assert expected == response.json()
