from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

T = TypeVar('T')


@dataclass
class CalculatorResult(Generic[T]):
    success: bool
    data: Optional[T] = None
    metadata: dict = field(default_factory=dict)
    errors: Optional[list[str]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def add_error(self, message: str) -> None:
        if self.errors is None:
            self.errors = []
        self.errors.append(message)
        self.success = False
