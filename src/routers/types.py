from fastapi import Body

SystemString64 = Body(pattern=r"^[\w\-\.]+$", min_length=1, max_length=64)

CasualString128 = Body(pattern=r"^[\w\-\.\(\),]+$", min_length=1, max_length=128)

integer_range_regex = r"^(\d+)(\.\.\d+)?$"
IntegerRange = Body(pattern=integer_range_regex)
