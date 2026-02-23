"""PromptPM core error types."""

from __future__ import annotations


class PromptPMError(Exception):
    """Base class for PromptPM errors."""

    code = "INTERNAL_ERROR"


class ValidationError(PromptPMError):
    """Error raised when prompt module validation fails."""

    code = "VALIDATION_ERROR"


class DependencyError(PromptPMError):
    """Error raised for dependency resolution failures."""

    code = "DEPENDENCY_ERROR"


class PublishConflictError(PromptPMError):
    """Error raised when publishing an already existing module version."""

    code = "PUBLISH_CONFLICT"
