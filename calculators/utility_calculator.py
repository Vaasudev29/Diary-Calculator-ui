from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any, List

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.batch import Batch
from models.utility import Utility
from models.exceptions import ValidationError, CalculationError


class UtilityCalculator(BaseCalculator):
    """Calculate utility consumption and costs for a Batch.

    Inputs:
      - batch: Batch
    Returns a breakdown per utility and total cost.
    """

    def validate_inputs(self, batch: Optional[Batch] = None, **kwargs) -> None:
        if batch is None:
            raise ValidationError('batch is required')
        if not isinstance(batch, Batch):
            raise ValidationError('batch must be a Batch instance')

    def compute(self, batch: Batch = None, **kwargs) -> CalculatorResult:
        total_cost = Decimal('0')
        breakdown: List[Dict[str, Any]] = []
        try:
            for u in batch.utilities:
                if not isinstance(u, Utility):
                    raise CalculationError('utilities must be Utility instances')
                cons = Decimal(u.consumption_per_batch)
                cost = Decimal(u.cost_per_unit) * cons
                breakdown.append({'name': u.name, 'unit': u.unit, 'consumption': float(cons), 'cost': float(cost)})
                total_cost += cost
        except Exception as e:
            raise CalculationError(f'Error computing utilities: {e}')

        data = {'breakdown': breakdown, 'total_utility_cost': float(total_cost)}
        return CalculatorResult(success=True, data=data)
