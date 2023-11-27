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


def test_get_quality(api_client: TestClient) -> None:
    response = api_client.get("/v1/datasets/qualities/1")
    assert response.status_code == http.client.OK
    expected = [
        {"name": "AutoCorrelation", "value": 0.6064659977703456},
        {"name": "CfsSubsetEval_DecisionStumpAUC", "value": 0.9067742570970945},
        {"name": "CfsSubsetEval_DecisionStumpErrRate", "value": 0.13251670378619154},
        {"name": "CfsSubsetEval_DecisionStumpKappa", "value": 0.6191022730108037},
        {"name": "CfsSubsetEval_NaiveBayesAUC", "value": 0.9067742570970945},
        {"name": "CfsSubsetEval_NaiveBayesErrRate", "value": 0.13251670378619154},
        {"name": "CfsSubsetEval_NaiveBayesKappa", "value": 0.6191022730108037},
        {"name": "CfsSubsetEval_kNN1NAUC", "value": 0.9067742570970945},
        {"name": "CfsSubsetEval_kNN1NErrRate", "value": 0.13251670378619154},
        {"name": "CfsSubsetEval_kNN1NKappa", "value": 0.6191022730108037},
        {"name": "ClassEntropy", "value": 1.189833856204398},
        {"name": "DecisionStumpAUC", "value": 0.8652735384332186},
        {"name": "DecisionStumpErrRate", "value": 0.22828507795100222},
        {"name": "DecisionStumpKappa", "value": 0.4503332218612649},
        {"name": "Dimensionality", "value": 0.043429844097995544},
        {"name": "EquivalentNumberOfAtts", "value": 26.839183802676523},
        {"name": "J48.00001.AUC", "value": 0.9391585368767195},
        {"name": "J48.00001.ErrRate", "value": 0.10356347438752785},
        {"name": "J48.00001.Kappa", "value": 0.7043302166347443},
        {"name": "J48.0001.AUC", "value": 0.9391585368767195},
        {"name": "J48.0001.ErrRate", "value": 0.10356347438752785},
        {"name": "J48.0001.Kappa", "value": 0.7043302166347443},
        {"name": "J48.001.AUC", "value": 0.9391585368767195},
        {"name": "J48.001.ErrRate", "value": 0.10356347438752785},
        {"name": "J48.001.Kappa", "value": 0.7043302166347443},
        {"name": "MajorityClassPercentage", "value": 76.16926503340757},
        {"name": "MajorityClassSize", "value": 684.0},
        {"name": "MaxAttributeEntropy", "value": 1.8215224482924186},
        {"name": "MaxKurtosisOfNumericAtts", "value": 13.215477213878724},
        {"name": "MaxMeansOfNumericAtts", "value": 1263.0946547884187},
        {"name": "MaxMutualInformation", "value": 0.40908953764451},
        {"name": "MaxNominalAttDistinctValues", "value": 7.0},
        {"name": "MaxSkewnessOfNumericAtts", "value": 3.7616019689156888},
        {"name": "MaxStdDevOfNumericAtts", "value": 1871.3991072665933},
        {"name": "MeanAttributeEntropy", "value": 0.2515351603742048},
        {"name": "MeanKurtosisOfNumericAtts", "value": 4.6480244352098286},
        {"name": "MeanMeansOfNumericAtts", "value": 348.50426818856715},
        {"name": "MeanMutualInformation", "value": 0.044331968697414056},
        {"name": "MeanNoiseToSignalRatio", "value": 4.673900071775454},
        {"name": "MeanNominalAttDistinctValues", "value": 1.6363636363636362},
        {"name": "MeanSkewnessOfNumericAtts", "value": 2.0269825910719437},
        {"name": "MeanStdDevOfNumericAtts", "value": 405.17326983791025},
        {"name": "MinAttributeEntropy", "value": -0.0},
        {"name": "MinKurtosisOfNumericAtts", "value": -0.9723842038435437},
        {"name": "MinMeansOfNumericAtts", "value": 1.1985489977728285},
        {"name": "MinMutualInformation", "value": 0.0},
        {"name": "MinNominalAttDistinctValues", "value": 0.0},
        {"name": "MinSkewnessOfNumericAtts", "value": 0.07299048442083138},
        {"name": "MinStdDevOfNumericAtts", "value": 0.871208280971892},
        {"name": "MinorityClassPercentage", "value": 0.8908685968819599},
        {"name": "MinorityClassSize", "value": 8.0},
        {"name": "NaiveBayesAUC", "value": 0.9315907109421729},
        {"name": "NaiveBayesErrRate", "value": 0.24610244988864144},
        {"name": "NaiveBayesKappa", "value": 0.5569590016631507},
        {"name": "NumberOfBinaryFeatures", "value": 4.0},
        {"name": "NumberOfClasses", "value": 5.0},
        {"name": "NumberOfFeatures", "value": 39.0},
        {"name": "NumberOfInstances", "value": 898.0},
        {"name": "NumberOfInstancesWithMissingValues", "value": 898.0},
        {"name": "NumberOfMissingValues", "value": 22175.0},
        {"name": "NumberOfNumericFeatures", "value": 6.0},
        {"name": "NumberOfSymbolicFeatures", "value": 33.0},
        {"name": "PercentageOfBinaryFeatures", "value": 10.256410256410255},
        {"name": "PercentageOfInstancesWithMissingValues", "value": 100.0},
        {"name": "PercentageOfMissingValues", "value": 63.317343384158534},
        {"name": "PercentageOfNumericFeatures", "value": 15.384615384615385},
        {"name": "PercentageOfSymbolicFeatures", "value": 84.61538461538461},
        {"name": "Quartile1AttributeEntropy", "value": 0.0},
        {"name": "Quartile1KurtosisOfNumericAtts", "value": -0.40305022089010156},
        {"name": "Quartile1MeansOfNumericAtts", "value": 3.025695155902005},
        {"name": "Quartile1MutualInformation", "value": 0.0},
        {"name": "Quartile1SkewnessOfNumericAtts", "value": 0.967384603629726},
        {"name": "Quartile1StdDevOfNumericAtts", "value": 10.505435772171138},
        {"name": "Quartile2AttributeEntropy", "value": 0.0},
        {"name": "Quartile2KurtosisOfNumericAtts", "value": 1.6372437439142264},
        {"name": "Quartile2MeansOfNumericAtts", "value": 21.222160356347437},
        {"name": "Quartile2MutualInformation", "value": 0.0},
        {"name": "Quartile2SkewnessOfNumericAtts", "value": 1.6547313364025702},
        {"name": "Quartile2StdDevOfNumericAtts", "value": 69.85338529046133},
        {"name": "Quartile3AttributeEntropy", "value": 0.2385631077559124},
        {"name": "Quartile3KurtosisOfNumericAtts", "value": 12.741748058445403},
        {"name": "Quartile3MeansOfNumericAtts", "value": 901.2636692650334},
        {"name": "Quartile3MutualInformation", "value": 0.0206465881071925},
        {"name": "Quartile3SkewnessOfNumericAtts", "value": 3.7546438249219056},
        {"name": "Quartile3StdDevOfNumericAtts", "value": 771.8590427889504},
        {"name": "REPTreeDepth1AUC", "value": 0.962680369298288},
        {"name": "REPTreeDepth1ErrRate", "value": 0.08463251670378619},
        {"name": "REPTreeDepth1Kappa", "value": 0.768583383630482},
        {"name": "REPTreeDepth2AUC", "value": 0.962680369298288},
        {"name": "REPTreeDepth2ErrRate", "value": 0.08463251670378619},
        {"name": "REPTreeDepth2Kappa", "value": 0.768583383630482},
        {"name": "REPTreeDepth3AUC", "value": 0.962680369298288},
        {"name": "REPTreeDepth3ErrRate", "value": 0.08463251670378619},
        {"name": "REPTreeDepth3Kappa", "value": 0.768583383630482},
        {"name": "RandomTreeDepth1AUC", "value": 0.9296999989655875},
        {"name": "RandomTreeDepth1ErrRate", "value": 0.0801781737193764},
        {"name": "RandomTreeDepth1Kappa", "value": 0.7953250436852635},
        {"name": "RandomTreeDepth2AUC", "value": 0.9296999989655875},
        {"name": "RandomTreeDepth2ErrRate", "value": 0.0801781737193764},
        {"name": "RandomTreeDepth2Kappa", "value": 0.7953250436852635},
        {"name": "RandomTreeDepth3AUC", "value": 0.9296999989655875},
        {"name": "RandomTreeDepth3ErrRate", "value": 0.0801781737193764},
        {"name": "RandomTreeDepth3Kappa", "value": 0.7953250436852635},
        {"name": "StdvNominalAttDistinctValues", "value": 1.5576059718800395},
        {"name": "kNN1NAUC", "value": 0.8721948540771287},
        {"name": "kNN1NErrRate", "value": 0.06347438752783964},
        {"name": "kNN1NKappa", "value": 0.8261102938928316},
    ]
    assert response.json() == expected
