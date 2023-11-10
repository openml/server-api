from typing import Literal

from fastapi import APIRouter

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])


@router.get("/qualities/list")
def list_qualities() -> (
    dict[
        Literal["data_qualities_list"],
        dict[
            Literal["quality"],
            list[str],
        ],
    ]
):
    return {"data_qualities_list": {"quality": []}}
