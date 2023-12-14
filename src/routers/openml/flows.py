from fastapi import APIRouter
from schemas.flows import Flow

router = APIRouter(prefix="/flows", tags=["flows"])


@router.get("/{flow_id}")
def get_flow(_: int) -> Flow:
    return Flow(
        id_=1,
        uploader=16,
        name="weka.ZeroR",
        class_name="weka.classifiers.rules.ZeroR",
        version=1,
        external_version="Weka_3.9.0_12024",
        description="Weka implementation of ZeroR",
        upload_date="2017-03-24T14:26:38",
        language="English",
        dependencies="Weka_3.9.0",
        parameter=[
            {
                "name": "-do-not-check-capabilities",
                "data_type": "flag",
                "default_value": [],
                "description": "If set,  classifier capabilities are not checked before classifier is built\n\t(use with caution).",  # noqa: E501
            },
            {
                "name": "batch-size",
                "data_type": "option",
                "default_value": [],
                "description": "The desired batch size for batch prediction  (default 100).",
            },
            {
                "name": "num-decimal-places",
                "data_type": "option",
                "default_value": [],
                "description": "The number of decimal places for the output of numbers in the model (default 2).",  # noqa: E501
            },
            {
                "name": "output-debug-info",
                "data_type": "flag",
                "default_value": [],
                "description": "If set,  classifier is run in debug mode and\n\tmay output additional info to the console",  # noqa: E501
            },
        ],
        subflows=[],
        tag=["OpenmlWeka", "weka"],
    )
