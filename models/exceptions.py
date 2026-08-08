from __future__ import annotations

class DairyError(Exception):
    """Base exception for domain errors."""
    pass


class ValidationError(DairyError):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


class CalculationError(DairyError):
    """Raised when a calculation fails or is invalid."""
    pass


class DataNotFoundError(DairyError):
    """Raised when required reference data is missing."""
    pass


class RepositoryError(DairyError):
    """Raised for repository / persistence related errors."""
    pass
