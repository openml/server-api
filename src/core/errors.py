"""RFC 9457 Problem Details for HTTP APIs.

This module provides RFC 9457 compliant error handling for the OpenML REST API.
See: https://www.rfc-editor.org/rfc/rfc9457.html
"""

from enum import IntEnum
from http import HTTPStatus
from typing import NoReturn

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# JSON-serializable extension value type for RFC 9457 problem details
type ExtensionValue = str | int | float | bool | None | list[str] | list[int]


class DatasetError(IntEnum):
    NOT_FOUND = 111
    NO_ACCESS = 112
    NO_DATA_FILE = 113


class ProblemDetail(BaseModel):
    """RFC 9457 Problem Details model.

    All fields are optional per the specification, but `type` defaults to "about:blank"
    when not provided. The `status` field is advisory and should match the HTTP status code.
    """

    type_: str = Field(
        default="about:blank",
        serialization_alias="type",
        description="A URI reference identifying the problem type. Defaults to 'about:blank'.",
    )
    title: str | None = Field(
        default=None,
        description="A short, human-readable summary of the problem type.",
    )
    status: int | None = Field(
        default=None,
        description="The HTTP status code. Advisory only, should match the actual status.",
    )
    detail: str | None = Field(
        default=None,
        description="A human-readable explanation specific to this occurrence of the problem.",
    )
    instance: str | None = Field(
        default=None,
        description="A URI reference identifying this specific occurrence of the problem.",
    )


class ProblemDetailError(Exception):
    """Exception that produces RFC 9457 compliant error responses.

    Usage:
        raise ProblemDetailException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Dataset 123 was not found.",
            title="Dataset Not Found",
            type_="https://openml.org/problems/dataset-not-found",
            code="111",  # Extension field for legacy error codes
        )
    """

    def __init__(
        self,
        status_code: HTTPStatus | int,
        detail: str | None = None,
        title: str | None = None,
        type_: str = "about:blank",
        instance: str | None = None,
        **extensions: ExtensionValue,
    ) -> None:
        self.status_code = int(status_code)
        self.problem = ProblemDetail(
            type_=type_,
            title=title,
            status=self.status_code,
            detail=detail,
            instance=instance,
        )
        self.extensions = extensions
        super().__init__(detail or title or "An error occurred")


def problem_detail_exception_handler(
    request: Request,  # noqa: ARG001
    exc: ProblemDetailError,
) -> JSONResponse:
    """FastAPI exception handler for ProblemDetailException.

    Returns a response with:
    - Content-Type: application/problem+json
    - RFC 9457 compliant JSON body
    """
    content = exc.problem.model_dump(by_alias=True, exclude_none=True)
    content.update(exc.extensions)

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        media_type="application/problem+json",
    )


# Problem type URIs for OpenML-specific errors
# These should be documented at the corresponding URLs
class ProblemType:
    """Problem type URIs for common OpenML errors."""

    # Dataset errors
    DATASET_NOT_FOUND = "https://openml.org/problems/dataset-not-found"
    DATASET_NO_ACCESS = "https://openml.org/problems/dataset-no-access"
    DATASET_NO_DATA_FILE = "https://openml.org/problems/dataset-no-data-file"
    DATASET_NOT_PROCESSED = "https://openml.org/problems/dataset-not-processed"
    DATASET_PROCESSING_ERROR = "https://openml.org/problems/dataset-processing-error"
    DATASET_NO_FEATURES = "https://openml.org/problems/dataset-no-features"
    DATASET_STATUS_TRANSITION = "https://openml.org/problems/dataset-status-transition"
    DATASET_NOT_OWNED = "https://openml.org/problems/dataset-not-owned"
    DATASET_ADMIN_ONLY = "https://openml.org/problems/dataset-admin-only"

    # Authentication/Authorization errors
    AUTHENTICATION_REQUIRED = "https://openml.org/problems/authentication-required"
    AUTHENTICATION_FAILED = "https://openml.org/problems/authentication-failed"
    FORBIDDEN = "https://openml.org/problems/forbidden"

    # Tag errors
    TAG_ALREADY_EXISTS = "https://openml.org/problems/tag-already-exists"

    # Search/List errors
    NO_RESULTS = "https://openml.org/problems/no-results"

    # Study errors
    STUDY_NOT_FOUND = "https://openml.org/problems/study-not-found"
    STUDY_PRIVATE = "https://openml.org/problems/study-private"
    STUDY_LEGACY = "https://openml.org/problems/study-legacy"
    STUDY_ALIAS_EXISTS = "https://openml.org/problems/study-alias-exists"
    STUDY_INVALID_TYPE = "https://openml.org/problems/study-invalid-type"
    STUDY_NOT_EDITABLE = "https://openml.org/problems/study-not-editable"
    STUDY_CONFLICT = "https://openml.org/problems/study-conflict"

    # Task errors
    TASK_NOT_FOUND = "https://openml.org/problems/task-not-found"
    TASK_TYPE_NOT_FOUND = "https://openml.org/problems/task-type-not-found"

    # Flow errors
    FLOW_NOT_FOUND = "https://openml.org/problems/flow-not-found"

    # Service errors
    SERVICE_NOT_FOUND = "https://openml.org/problems/service-not-found"

    # Internal errors
    INTERNAL_ERROR = "https://openml.org/problems/internal-error"


# Human-readable titles for problem types
PROBLEM_TITLES: dict[str, str] = {
    ProblemType.DATASET_NOT_FOUND: "Dataset Not Found",
    ProblemType.DATASET_NO_ACCESS: "Dataset Access Denied",
    ProblemType.DATASET_NO_DATA_FILE: "Dataset Data File Missing",
    ProblemType.DATASET_NOT_PROCESSED: "Dataset Not Processed",
    ProblemType.DATASET_PROCESSING_ERROR: "Dataset Processing Error",
    ProblemType.DATASET_NO_FEATURES: "Dataset Features Not Available",
    ProblemType.DATASET_STATUS_TRANSITION: "Invalid Status Transition",
    ProblemType.DATASET_NOT_OWNED: "Dataset Not Owned",
    ProblemType.DATASET_ADMIN_ONLY: "Administrator Only",
    ProblemType.AUTHENTICATION_REQUIRED: "Authentication Required",
    ProblemType.AUTHENTICATION_FAILED: "Authentication Failed",
    ProblemType.FORBIDDEN: "Forbidden",
    ProblemType.TAG_ALREADY_EXISTS: "Tag Already Exists",
    ProblemType.NO_RESULTS: "No Results Found",
    ProblemType.STUDY_NOT_FOUND: "Study Not Found",
    ProblemType.STUDY_PRIVATE: "Study Is Private",
    ProblemType.STUDY_LEGACY: "Legacy Study Not Supported",
    ProblemType.STUDY_ALIAS_EXISTS: "Study Alias Already Exists",
    ProblemType.STUDY_INVALID_TYPE: "Invalid Study Type",
    ProblemType.STUDY_NOT_EDITABLE: "Study Not Editable",
    ProblemType.STUDY_CONFLICT: "Study Conflict",
    ProblemType.TASK_NOT_FOUND: "Task Not Found",
    ProblemType.TASK_TYPE_NOT_FOUND: "Task Type Not Found",
    ProblemType.FLOW_NOT_FOUND: "Flow Not Found",
    ProblemType.SERVICE_NOT_FOUND: "Service Not Found",
    ProblemType.INTERNAL_ERROR: "Internal Server Error",
}


def raise_problem(
    status_code: HTTPStatus | int,
    type_: str,
    detail: str,
    *,
    instance: str | None = None,
    code: int | str | None = None,
    **extensions: ExtensionValue,
) -> NoReturn:
    """Helper function to raise RFC 9457 compliant errors.

    Args:
        status_code: HTTP status code for the response.
        type_: Problem type URI identifying the error class.
        detail: Human-readable explanation of this specific error occurrence.
        instance: Optional URI identifying this specific error occurrence.
        code: Optional legacy OpenML error code (for backwards compatibility).
        **extensions: Additional extension fields to include in the response.
    """
    title = PROBLEM_TITLES.get(type_)
    if code is not None:
        extensions["code"] = str(code)
    raise ProblemDetailError(
        status_code=status_code,
        detail=detail,
        title=title,
        type_=type_,
        instance=instance,
        **extensions,
    )
