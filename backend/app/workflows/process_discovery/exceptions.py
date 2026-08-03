class ProcessDiscoveryWorkflowError(Exception):
    """Base exception for workflow construction and validation."""


class WorkflowValidationError(ProcessDiscoveryWorkflowError, ValueError):
    """Raised for invalid workflow input."""
