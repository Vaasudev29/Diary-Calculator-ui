from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.exceptions import ValidationError


class PackagingCalculator(BaseCalculator):
    """Calculate packaging requirements and costs.

    Inputs:
      - production_quantity (kg)
      - package_size (kg)
      - package_cost_per_unit

    Outputs:
      - units_required, total_packaging_cost
    """

    def validate_inputs(self, production_quantity: Optional[Decimal] = None, package_size: Optional[Decimal] = None,
                        package_cost_per_unit: Optional[Decimal] = None, **kwargs) -> None:
        try:
            pq = Decimal(production_quantity)
            ps = Decimal(package_size)
        except Exception:
            raise ValidationError('production_quantity and package_size must be numeric')
        if pq <= 0 or ps <= 0:
            raise ValidationError('production_quantity and package_size must be positive')

    def compute(self, production_quantity: Decimal = None, package_size: Decimal = None, package_cost_per_unit: Decimal = None, **kwargs) -> CalculatorResult:
        pq = Decimal(production_quantity)
        ps = Decimal(package_size)
        units = (pq / ps).to_integral_value(rounding='ROUND_UP')
        cost_per = Decimal(package_cost_per_unit) if package_cost_per_unit is not None else Decimal('0')
        total_cost = units * cost_per
        return CalculatorResult(success=True, data={'units_required': int(units), 'total_packaging_cost': float(total_cost)})
