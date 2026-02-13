"""RFC 9457 Problem Details for HTTP APIs.

This module provides RFC 9457 compliant error handling for the OpenML REST API.
See: https://www.rfc-editor.org/rfc/rfc9457.html
"""

from enum import IntEnum
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse


class DatasetError(IntEnum):
    NOT_FOUND = 111
    NO_ACCESS = 112
    NO_DATA_FILE = 113


# =============================================================================
# Base Exception
# =============================================================================


class ProblemDetailError(Exception):
    """Base exception for RFC 9457 compliant error responses.

    Subclasses should define class attributes:
        - uri: The problem type URI
        - title: Human-readable title
        - status_code: HTTP status code

    The status_code can be overridden per-instance for backwards compatibility.
    """

    uri: str = "about:blank"
    title: str = "An error occurred"
    _default_status_code: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        detail: str,
        *,
        code: int | str | None = None,
        instance: str | None = None,
        status_code: HTTPStatus | None = None,
    ) -> None:
        self.detail = detail
        self.code = code
        self.instance = instance
        self._status_code_override = status_code
        super().__init__(detail)

    @property
    def status_code(self) -> HTTPStatus:
        """Return the status code, preferring instance override over class default."""
        if self._status_code_override is not None:
            return self._status_code_override
        return self._default_status_code


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
        content["code"] = str(exc.code)
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
    """Raised when a dataset cannot be found.

    # Future: detail=f"Dataset {dataset_id} not found."
    # Future: validate dataset_id is positive int
    """

    uri = "https://openml.org/problems/dataset-not-found"
    title = "Dataset Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND


class DatasetNoAccessError(ProblemDetailError):
    """Raised when user doesn't have access to a dataset.

    # Future: detail=f"Access denied to dataset {dataset_id}."
    # Future: validate dataset_id is positive int
    """

    uri = "https://openml.org/problems/dataset-no-access"
    title = "Dataset Access Denied"
    _default_status_code = HTTPStatus.FORBIDDEN


class DatasetNoDataFileError(ProblemDetailError):
    """Raised when a dataset's data file is missing.

    # Future: detail=f"Data file for dataset {dataset_id} not found."
    # Future: validate dataset_id is positive int
    """

    uri = "https://openml.org/problems/dataset-no-data-file"
    title = "Dataset Data File Missing"
    _default_status_code = HTTPStatus.PRECONDITION_FAILED


class DatasetNotProcessedError(ProblemDetailError):
    """Raised when a dataset has not been processed yet.

    # Future: detail=f"Dataset {dataset_id} has not been processed yet."
    # Future: validate dataset_id is positive int
    """

    uri = "https://openml.org/problems/dataset-not-processed"
    title = "Dataset Not Processed"
    _default_status_code = HTTPStatus.PRECONDITION_FAILED


class DatasetProcessingError(ProblemDetailError):
    """Raised when a dataset had an error during processing.

    # Future: detail=f"Dataset {dataset_id} encountered an error during processing."
    # Future: validate dataset_id is positive int
    """

    uri = "https://openml.org/problems/dataset-processing-error"
    title = "Dataset Processing Error"
    _default_status_code = HTTPStatus.PRECONDITION_FAILED


class DatasetNoFeaturesError(ProblemDetailError):
    """Raised when a dataset has no features available.

    # Future: detail=f"No features found for dataset {dataset_id}."
    # Future: validate dataset_id is positive int
    """

    uri = "https://openml.org/problems/dataset-no-features"
    title = "Dataset Features Not Available"
    _default_status_code = HTTPStatus.PRECONDITION_FAILED


class DatasetStatusTransitionError(ProblemDetailError):
    """Raised when an invalid dataset status transition is attempted.

    # Future: detail=f"Cannot transition dataset {dataset_id} from {from_status} to {to_status}."
    # Future: validate statuses are valid DatasetStatus values
    """

    uri = "https://openml.org/problems/dataset-status-transition"
    title = "Invalid Status Transition"
    _default_status_code = HTTPStatus.PRECONDITION_FAILED


class DatasetNotOwnedError(ProblemDetailError):
    """Raised when user tries to modify a dataset they don't own.

    # Future: detail=f"Dataset {dataset_id} is not owned by you."
    # Future: validate dataset_id is positive int
    """

    uri = "https://openml.org/problems/dataset-not-owned"
    title = "Dataset Not Owned"
    _default_status_code = HTTPStatus.FORBIDDEN


class DatasetAdminOnlyError(ProblemDetailError):
    """Raised when a non-admin tries to perform an admin-only action.

    # Future: detail=f"Only administrators can {action}."
    # Future: validate action is non-empty string
    """

    uri = "https://openml.org/problems/dataset-admin-only"
    title = "Administrator Only"
    _default_status_code = HTTPStatus.FORBIDDEN


# =============================================================================
# Authentication/Authorization Errors
# =============================================================================


class AuthenticationRequiredError(ProblemDetailError):
    """Raised when authentication is required but not provided.

    # Future: detail=f"{action} requires authentication."
    # Future: validate action is non-empty string
    """

    uri = "https://openml.org/problems/authentication-required"
    title = "Authentication Required"
    _default_status_code = HTTPStatus.UNAUTHORIZED


class AuthenticationFailedError(ProblemDetailError):
    """Raised when authentication credentials are invalid.

    # Future: detail="Authentication failed. Invalid or expired credentials."
    """

    uri = "https://openml.org/problems/authentication-failed"
    title = "Authentication Failed"
    _default_status_code = HTTPStatus.UNAUTHORIZED


class ForbiddenError(ProblemDetailError):
    """Raised when user is authenticated but not authorized.

    # Future: detail=f"You do not have permission to {action}."
    # Future: validate action is non-empty string
    """

    uri = "https://openml.org/problems/forbidden"
    title = "Forbidden"
    _default_status_code = HTTPStatus.FORBIDDEN


# =============================================================================
# Tag Errors
# =============================================================================


class TagAlreadyExistsError(ProblemDetailError):
    """Raised when trying to add a tag that already exists.

    # Future: detail=f"Entity {entity_id} is already tagged with '{tag}'."
    # Future: validate entity_id is positive int, tag is non-empty string
    """

    uri = "https://openml.org/problems/tag-already-exists"
    title = "Tag Already Exists"
    _default_status_code = HTTPStatus.CONFLICT


# =============================================================================
# Search/List Errors
# =============================================================================


class NoResultsError(ProblemDetailError):
    """Raised when a search returns no results.

    # Future: detail="No results match the search criteria."
    """

    uri = "https://openml.org/problems/no-results"
    title = "No Results Found"
    _default_status_code = HTTPStatus.NOT_FOUND


# =============================================================================
# Study Errors
# =============================================================================


class StudyNotFoundError(ProblemDetailError):
    """Raised when a study cannot be found.

    # Future: detail=f"Study {study_id} not found."
    # Future: validate study_id is positive int or valid alias string
    """

    uri = "https://openml.org/problems/study-not-found"
    title = "Study Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND


class StudyPrivateError(ProblemDetailError):
    """Raised when trying to access a private study without permission.

    # Future: detail=f"Study {study_id} is private."
    # Future: validate study_id is positive int
    """

    uri = "https://openml.org/problems/study-private"
    title = "Study Is Private"
    _default_status_code = HTTPStatus.FORBIDDEN


class StudyLegacyError(ProblemDetailError):
    """Raised when trying to access a legacy study that's no longer supported.

    # Future: detail=f"Study {study_id} is a legacy study and no longer supported."
    # Future: validate study_id is positive int
    """

    uri = "https://openml.org/problems/study-legacy"
    title = "Legacy Study Not Supported"
    _default_status_code = HTTPStatus.GONE


class StudyAliasExistsError(ProblemDetailError):
    """Raised when trying to create a study with an alias that already exists.

    # Future: detail=f"Study alias '{alias}' already exists."
    # Future: validate alias is non-empty string
    """

    uri = "https://openml.org/problems/study-alias-exists"
    title = "Study Alias Already Exists"
    _default_status_code = HTTPStatus.CONFLICT


class StudyInvalidTypeError(ProblemDetailError):
    """Raised when study type configuration is invalid.

    # Future: detail=f"Cannot create {study_type} study with {invalid_field}."
    """

    uri = "https://openml.org/problems/study-invalid-type"
    title = "Invalid Study Type"
    _default_status_code = HTTPStatus.BAD_REQUEST


class StudyNotEditableError(ProblemDetailError):
    """Raised when trying to edit a study that cannot be edited.

    # Future: detail=f"Study {study_id} cannot be edited. {reason}"
    # Future: validate study_id is positive int
    """

    uri = "https://openml.org/problems/study-not-editable"
    title = "Study Not Editable"
    _default_status_code = HTTPStatus.FORBIDDEN


class StudyConflictError(ProblemDetailError):
    """Raised when there's a conflict with study data (e.g., duplicate attachment).

    # Future: detail=f"Conflict: {reason}"
    """

    uri = "https://openml.org/problems/study-conflict"
    title = "Study Conflict"
    _default_status_code = HTTPStatus.CONFLICT


# =============================================================================
# Task Errors
# =============================================================================


class TaskNotFoundError(ProblemDetailError):
    """Raised when a task cannot be found.

    # Future: detail=f"Task {task_id} not found."
    # Future: validate task_id is positive int
    """

    uri = "https://openml.org/problems/task-not-found"
    title = "Task Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND


class TaskTypeNotFoundError(ProblemDetailError):
    """Raised when a task type cannot be found.

    # Future: detail=f"Task type {task_type_id} not found."
    # Future: validate task_type_id is positive int
    """

    uri = "https://openml.org/problems/task-type-not-found"
    title = "Task Type Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND


# =============================================================================
# Flow Errors
# =============================================================================


class FlowNotFoundError(ProblemDetailError):
    """Raised when a flow cannot be found.

    # Future: detail=f"Flow {flow_id} not found." or "Flow '{name}' version '{version}' not found."
    # Future: validate flow_id is positive int
    """

    uri = "https://openml.org/problems/flow-not-found"
    title = "Flow Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND


# =============================================================================
# Service Errors
# =============================================================================


class ServiceNotFoundError(ProblemDetailError):
    """Raised when a service cannot be found.

    # Future: detail=f"Service {service_id} not found."
    # Future: validate service_id is positive int
    """

    uri = "https://openml.org/problems/service-not-found"
    title = "Service Not Found"
    _default_status_code = HTTPStatus.NOT_FOUND


# =============================================================================
# Internal Errors
# =============================================================================


class InternalError(ProblemDetailError):
    """Raised for unexpected internal server errors.

    # Future: detail="An unexpected error occurred. Please try again later."
    """

    uri = "https://openml.org/problems/internal-error"
    title = "Internal Server Error"
    _default_status_code = HTTPStatus.INTERNAL_SERVER_ERROR


# =============================================================================
# Backwards Compatibility
# =============================================================================


class ProblemType:
    """Problem type URIs for common OpenML errors.

    Deprecated: Use the specific exception classes directly instead.
    """

    DATASET_NOT_FOUND = DatasetNotFoundError.uri
    DATASET_NO_ACCESS = DatasetNoAccessError.uri
    DATASET_NO_DATA_FILE = DatasetNoDataFileError.uri
    DATASET_NOT_PROCESSED = DatasetNotProcessedError.uri
    DATASET_PROCESSING_ERROR = DatasetProcessingError.uri
    DATASET_NO_FEATURES = DatasetNoFeaturesError.uri
    DATASET_STATUS_TRANSITION = DatasetStatusTransitionError.uri
    DATASET_NOT_OWNED = DatasetNotOwnedError.uri
    DATASET_ADMIN_ONLY = DatasetAdminOnlyError.uri
    AUTHENTICATION_REQUIRED = AuthenticationRequiredError.uri
    AUTHENTICATION_FAILED = AuthenticationFailedError.uri
    FORBIDDEN = ForbiddenError.uri
    TAG_ALREADY_EXISTS = TagAlreadyExistsError.uri
    NO_RESULTS = NoResultsError.uri
    STUDY_NOT_FOUND = StudyNotFoundError.uri
    STUDY_PRIVATE = StudyPrivateError.uri
    STUDY_LEGACY = StudyLegacyError.uri
    STUDY_ALIAS_EXISTS = StudyAliasExistsError.uri
    STUDY_INVALID_TYPE = StudyInvalidTypeError.uri
    STUDY_NOT_EDITABLE = StudyNotEditableError.uri
    STUDY_CONFLICT = StudyConflictError.uri
    TASK_NOT_FOUND = TaskNotFoundError.uri
    TASK_TYPE_NOT_FOUND = TaskTypeNotFoundError.uri
    FLOW_NOT_FOUND = FlowNotFoundError.uri
    SERVICE_NOT_FOUND = ServiceNotFoundError.uri
    INTERNAL_ERROR = InternalError.uri
