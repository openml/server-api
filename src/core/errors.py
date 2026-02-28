"""RFC 9457 Problem Details for HTTP APIs.

This module provides RFC 9457 compliant error handling for the OpenML REST API.
See: https://www.rfc-editor.org/rfc/rfc9457.html
"""

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

# =============================================================================
# Base Exception
# =============================================================================


class ProblemDetailError(Exception):
    """Base exception for RFC 9457 compliant error responses.

    Subclasses should define class attributes:
        - uri: The problem type URI
        - title: Human-readable title
        - _default_status_code: HTTP status code
        - _default_code: Legacy error code (optional)

    The status_code and code can be overridden per-instance.
    """

    uri: str = "about:blank"
    title: str = "An error occurred"
    _default_status_code: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR
    _default_code: int | None = None

    def __init__(
        self,
        detail: str,
        *,
        code: int | str | None = None,
        instance: str | None = None,
        status_code: HTTPStatus | None = None,
    ) -> None:
        """Initialize a ProblemDetailError.

        Args:
            detail: Human-readable error description.
            code: Optional error code (legacy).
            instance: Optional URI identifying the specific error instance.
            status_code: Optional HTTP status code override.

        """
        self.detail = detail
        self._code_override = code
        self.instance = instance
        self._status_code_override = status_code
        super().__init__(detail)

    @property
    def status_code(self) -> HTTPStatus:
        """Return the status code, preferring instance override over class default."""
        if self._status_code_override is not None:
            return self._status_code_override
        return self._default_status_code

    @property
    def code(self) -> int | str | None:
        """Return the code, preferring instance override over class default."""
        if self._code_override is not None:
            return self._code_override
        return self._default_code


def problem_detail_exception_handler(
    request: Request,  # noqa: ARG001
    exc: ProblemDetailError,
) -> JSONResponse:
    """FastAPI exception handler for ProblemDetailError.

    Returns a response with:
    - Content-Type: application/problem+json
    - RFC 9457 compliant JSON body
    """
    content: dict[str, str | int] = {
        "type": exc.uri,
        "title": exc.title,
        "status": int(exc.status_code),
        "detail": exc.detail,
    }
    if exc.code is not None:
        content["code"] = exc.code
    if exc.instance is not None:
        content["instance"] = exc.instance

    return JSONResponse(
        status_code=int(exc.status_code),
        content=content,
        media_type="application/problem+json",
    )


# =============================================================================
# Dataset Errors
# =============================================================================


class DatasetNotFoundError(ProblemDetailError):
    """Raised when a dataset cannot be found."""

    uri = "https://openml.org/problems/dataset-not-found"
    title = "Dataset Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND
    _default_code = 111


class DatasetNoAccessError(ProblemDetailError):
    """Raised when user doesn't have access to a dataset."""

    uri = "https://openml.org/problems/dataset-no-access"
    title = "Dataset Access Denied"
    _default_status_code = HTTPStatus.FORBIDDEN
    _default_code = 112


class DatasetNoDataFileError(ProblemDetailError):
    """Raised when a dataset's data file is missing."""

    uri = "https://openml.org/problems/dataset-no-data-file"
    title = "Dataset Data File Missing"
    _default_status_code = HTTPStatus.PRECONDITION_FAILED
    _default_code = 113


class DatasetNotProcessedError(ProblemDetailError):
    """Raised when a dataset has not been processed yet."""

    uri = "https://openml.org/problems/dataset-not-processed"
    title = "Dataset Not Processed"
    _default_status_code = HTTPStatus.PRECONDITION_FAILED
    _default_code = 273


class DatasetProcessingError(ProblemDetailError):
    """Raised when a dataset had an error during processing."""

    uri = "https://openml.org/problems/dataset-processing-error"
    title = "Dataset Processing Error"
    _default_status_code = HTTPStatus.PRECONDITION_FAILED
    _default_code = 274


class DatasetNoFeaturesError(ProblemDetailError):
    """Raised when a dataset has no features available."""

    uri = "https://openml.org/problems/dataset-no-features"
    title = "Dataset Features Not Available"
    _default_status_code = HTTPStatus.PRECONDITION_FAILED
    _default_code = 272


class DatasetStatusTransitionError(ProblemDetailError):
    """Raised when an invalid dataset status transition is attempted."""

    uri = "https://openml.org/problems/dataset-status-transition"
    title = "Invalid Status Transition"
    _default_status_code = HTTPStatus.PRECONDITION_FAILED
    _default_code = 694


class DatasetNotOwnedError(ProblemDetailError):
    """Raised when user tries to modify a dataset they don't own."""

    uri = "https://openml.org/problems/dataset-not-owned"
    title = "Dataset Not Owned"
    _default_status_code = HTTPStatus.FORBIDDEN
    _default_code = 693


class DatasetAdminOnlyError(ProblemDetailError):
    """Raised when a non-admin tries to perform an admin-only action."""

    uri = "https://openml.org/problems/dataset-admin-only"
    title = "Administrator Only"
    _default_status_code = HTTPStatus.FORBIDDEN
    _default_code = 696


# =============================================================================
# Authentication/Authorization Errors
# =============================================================================


class AuthenticationRequiredError(ProblemDetailError):
    """Raised when authentication is required but not provided."""

    uri = "https://openml.org/problems/authentication-required"
    title = "Authentication Required"
    _default_status_code = HTTPStatus.UNAUTHORIZED


class AuthenticationFailedError(ProblemDetailError):
    """Raised when authentication credentials are invalid."""

    uri = "https://openml.org/problems/authentication-failed"
    title = "Authentication Failed"
    _default_status_code = HTTPStatus.UNAUTHORIZED
    _default_code = 103


class ForbiddenError(ProblemDetailError):
    """Raised when user is authenticated but not authorized."""

    uri = "https://openml.org/problems/forbidden"
    title = "Forbidden"
    _default_status_code = HTTPStatus.FORBIDDEN


# =============================================================================
# Tag Errors
# =============================================================================


class TagAlreadyExistsError(ProblemDetailError):
    """Raised when trying to add a tag that already exists."""

    uri = "https://openml.org/problems/tag-already-exists"
    title = "Tag Already Exists"
    _default_status_code = HTTPStatus.CONFLICT
    _default_code = 473


# =============================================================================
# Search/List Errors
# =============================================================================


class NoResultsError(ProblemDetailError):
    """Raised when a search returns no results."""

    uri = "https://openml.org/problems/no-results"
    title = "No Results Found"
    _default_status_code = HTTPStatus.NOT_FOUND
    _default_code = 372


# =============================================================================
# Study Errors
# =============================================================================


class StudyNotFoundError(ProblemDetailError):
    """Raised when a study cannot be found."""

    uri = "https://openml.org/problems/study-not-found"
    title = "Study Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND


class StudyPrivateError(ProblemDetailError):
    """Raised when trying to access a private study without permission."""

    uri = "https://openml.org/problems/study-private"
    title = "Study Is Private"
    _default_status_code = HTTPStatus.FORBIDDEN


class StudyLegacyError(ProblemDetailError):
    """Raised when trying to access a legacy study that's no longer supported."""

    uri = "https://openml.org/problems/study-legacy"
    title = "Legacy Study Not Supported"
    _default_status_code = HTTPStatus.GONE


class StudyAliasExistsError(ProblemDetailError):
    """Raised when trying to create a study with an alias that already exists."""

    uri = "https://openml.org/problems/study-alias-exists"
    title = "Study Alias Already Exists"
    _default_status_code = HTTPStatus.CONFLICT


class StudyInvalidTypeError(ProblemDetailError):
    """Raised when study type configuration is invalid."""

    uri = "https://openml.org/problems/study-invalid-type"
    title = "Invalid Study Type"
    _default_status_code = HTTPStatus.BAD_REQUEST


class StudyNotEditableError(ProblemDetailError):
    """Raised when trying to edit a study that cannot be edited."""

    uri = "https://openml.org/problems/study-not-editable"
    title = "Study Not Editable"
    _default_status_code = HTTPStatus.FORBIDDEN


class StudyConflictError(ProblemDetailError):
    """Raised when there's a conflict with study data (e.g., duplicate attachment)."""

    uri = "https://openml.org/problems/study-conflict"
    title = "Study Conflict"
    _default_status_code = HTTPStatus.CONFLICT


# =============================================================================
# Task Errors
# =============================================================================


class TaskNotFoundError(ProblemDetailError):
    """Raised when a task cannot be found."""

    uri = "https://openml.org/problems/task-not-found"
    title = "Task Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND


class TaskTypeNotFoundError(ProblemDetailError):
    """Raised when a task type cannot be found."""

    uri = "https://openml.org/problems/task-type-not-found"
    title = "Task Type Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND
    _default_code = 241


# =============================================================================
# Flow Errors
# =============================================================================


class FlowNotFoundError(ProblemDetailError):
    """Raised when a flow cannot be found."""

    uri = "https://openml.org/problems/flow-not-found"
    title = "Flow Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND


# =============================================================================
# Service Errors
# =============================================================================


class ServiceNotFoundError(ProblemDetailError):
    """Raised when a service cannot be found."""

    uri = "https://openml.org/problems/service-not-found"
    title = "Service Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND


# =============================================================================
# Internal Errors
# =============================================================================


class InternalError(ProblemDetailError):
    """Raised for unexpected internal server errors."""

    uri = "https://openml.org/problems/internal-error"
    title = "Internal Server Error"
    _default_status_code = HTTPStatus.INTERNAL_SERVER_ERROR
