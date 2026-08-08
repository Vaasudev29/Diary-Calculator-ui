from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.production_cost import ProductionCost
from models.exceptions import ValidationError


class ProfitCalculator(BaseCalculator):
    """Calculate profit given production cost and revenue inputs.

    Inputs:
      - production_cost: ProductionCost or numeric total_cost
      - revenue: numeric revenue amount (total)

    Outputs:
      - profit, margin_pct
    """

    def validate_inputs(self, production_cost: Optional[ProductionCost] = None, revenue: Optional[Decimal] = None, **kwargs) -> None:
        if production_cost is None and revenue is None:
            raise ValidationError('production_cost and revenue are required')

    def compute(self, production_cost: ProductionCost = None, revenue: Decimal = None, **kwargs) -> CalculatorResult:
        if production_cost is None:
            raise ValidationError('production_cost is required')
        total_cost = Decimal(production_cost.total_cost)
        rev = Decimal(revenue)
        profit = rev - total_cost
        margin = (profit / rev * Decimal('100')) if rev != 0 else Decimal('0')
        return CalculatorResult(success=True, data={'profit': float(profit), 'margin_pct': float(margin)})
