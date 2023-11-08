from typing import Annotated

from pydantic import StringConstraints

SystemString64 = Annotated[
    str,
    StringConstraints(pattern=r"[a-zA-Z0-9_\-\.]+", min_length=1, max_length=64),
]
