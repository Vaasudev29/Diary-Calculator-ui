from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.production_cost import ProductionCost
from models.batch import Batch
from models.ingredient import Ingredient
from models.exceptions import ValidationError, CalculationError


class ProductionCostCalculator(BaseCalculator):
    """Calculate production cost for a Batch.

    Inputs:
      - batch: Batch object containing input_materials and utilities
      - labor_cost (optional)
      - overhead (optional)

    Returns ProductionCost in CalculatorResult.data
    """

    def validate_inputs(self, batch: Optional[Batch] = None, **kwargs) -> None:
        if batch is None:
            raise ValidationError('batch is required')
        if not isinstance(batch, Batch):
            raise ValidationError('batch must be a Batch instance')

    def compute(self, batch: Batch = None, labor_cost: Optional[Decimal] = None, overhead: Optional[Decimal] = None, **kwargs) -> CalculatorResult:
        # Material cost
        material_cost = Decimal('0')
        try:
            for ing in batch.input_materials:
                if not isinstance(ing, Ingredient):
                    raise CalculationError('input_materials must contain Ingredient instances')
                price = ing.product.cost_per_unit
                qty = Decimal(ing.quantity)
                material_cost += price * qty
        except Exception as e:
            raise CalculationError(f'Error computing material cost: {e}')

        # Utility cost
        utility_cost = Decimal('0')
        try:
            for u in batch.utilities:
                utility_cost += Decimal(u.consumption_per_batch) * Decimal(u.cost_per_unit)
        except Exception as e:
            raise CalculationError(f'Error computing utility cost: {e}')

        labor = Decimal(labor_cost) if labor_cost is not None else Decimal('0')
        over = Decimal(overhead) if overhead is not None else Decimal('0')

        pc = ProductionCost(material_cost=material_cost, utility_cost=utility_cost, labor_cost=labor, overhead=over)
        # standardized summary placed in metadata
        metadata = {'result_summary': {'net_total_cost': float(pc.total_cost)}}
        return CalculatorResult(success=True, data=pc, metadata=metadata)
