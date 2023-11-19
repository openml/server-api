from typing import Annotated

from fastapi import Body

SystemString64 = Annotated[
    str,
    Body(pattern=r"^[\w\-\.]+$", min_length=1, max_length=64),
]

CasualString128 = Body(patter=r"^[\w\-\.\(\),]+$", min_length=1, max_length=128)
