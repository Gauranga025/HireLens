from typing import Any, Dict, List, Optional


class DocumentProcessingError(Exception):
    """Base exception for document processing errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class UnsupportedFileTypeError(DocumentProcessingError):
    """Exception raised when an unsupported file type is provided."""

    def __init__(self, file_type: str, supported_types: List[str]) -> None:
        self.file_type = file_type
        self.supported_types = supported_types
        message = f"Unsupported file type: {file_type}. Supported types: {', '.join(supported_types)}"
        super().__init__(message, {"file_type": file_type, "supported_types": supported_types})


class ValidationError(Exception):
    """Exception raised for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        self.message = message
        self.field = field
        super().__init__(self.message)


class MatchingError(Exception):
    """Exception raised during resume-job matching process."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
