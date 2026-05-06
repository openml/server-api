from typing import Annotated

from pydantic import Field

SystemString64 = Annotated[str, Field(pattern=r"^[\w\-\.]+$", min_length=1, max_length=64)]
CasualString128 = Annotated[str, Field(pattern=r"^[\w\-\.\(\),]+$", min_length=1, max_length=128)]
Identifier = Annotated[int, Field(gt=0)]

integer_range_regex = r"^(\d+)(\.\.\d+)?$"
IntegerRange = Annotated[
    str,
    Field(
        pattern=integer_range_regex,
        description="Either a single integer, or a range defined as `low..high`, where"
        "`low` and `high` are inclusive integer bounds of the range.",
        examples=["12", "3..150"],
    ),
]
