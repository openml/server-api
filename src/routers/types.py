from typing import Annotated

from fastapi import Body

SystemString64 = Annotated[
    str,
    Body(pattern=r"^[a-zA-Z0-9_\-\.]+$", min_length=1, max_length=64),
]
