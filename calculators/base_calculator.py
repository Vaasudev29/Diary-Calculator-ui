from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from models.result import CalculatorResult
from models.exceptions import ValidationError, CalculationError


class BaseCalculator(ABC):
    """Abstract base class for calculators.

    Subclasses must implement validate_inputs and compute. Use run(...) to perform
    validation and computation with standardized error handling and a CalculatorResult return.
    """

    def __init__(self, repository: Optional[Any] = None) -> None:
        """Initialize calculator with an optional repository/data source."""
        self.repository = repository

    @abstractmethod
    def validate_inputs(self, **kwargs) -> None:
        """Validate inputs for the calculation. Should raise ValidationError on problems."""
        raise NotImplementedError

    @abstractmethod
    def compute(self, **kwargs) -> CalculatorResult:
        """Perform the calculation. Must return a CalculatorResult."""
        raise NotImplementedError

    def explain(self, **kwargs) -> Dict[str, Any]:
        """Optional: return an explanation / audit trail of calculation steps."""
        return {}

    def run(self, **kwargs) -> CalculatorResult:
        """Convenience method: validate, compute, and handle exceptions uniformly.

        Returns a CalculatorResult with success flag and errors populated on failure.
        """
        try:
            self.validate_inputs(**kwargs)
            result = self.compute(**kwargs)
            if not isinstance(result, CalculatorResult):
                raise CalculationError('compute must return a CalculatorResult')
            return result
        except ValidationError as ve:
            res = CalculatorResult(success=False, data=None, errors=[str(ve)])
            return res
        except CalculationError as ce:
            res = CalculatorResult(success=False, data=None, errors=[str(ce)])
            return res
        except Exception as e:
            # Unexpected errors are captured and returned as failure result
            res = CalculatorResult(success=False, data=None, errors=[str(e)])
            return res
