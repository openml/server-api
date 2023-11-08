from typing import Annotated

from fastapi import Query

SystemString64 = Annotated[
    str,
    Query(pattern=r"^[a-zA-Z0-9_\-\.]+$", min_length=1, max_length=64),
]
