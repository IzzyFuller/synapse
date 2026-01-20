"""Error models for standardized error handling in pub-sub messages."""

from typing import Optional

from fasteroutcomes_pubsub.models.base import CamelCaseModel


class ErrorDetails(CamelCaseModel):
    """Additional structured error details."""

    file_path: Optional[str] = None
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None


class ErrorInfo(CamelCaseModel):
    """Structured error information."""

    type: str  # Error type (validation, file_not_found, processing_error, etc.)
    message: str
    details: Optional[ErrorDetails] = None
