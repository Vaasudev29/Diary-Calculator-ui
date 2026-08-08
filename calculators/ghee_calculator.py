from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.milk_composition import MilkComposition
from models.exceptions import ValidationError, CalculationError
from utils.result_helpers import build_result_summary


class GheeCalculator(BaseCalculator):
    """Compute ghee yield from butter using an approximate conversion factor.

    Inputs:
      - butter_mass_kg or butter_yield_factor and batch_size
    Outputs:
      - ghee_mass_kg
    """

    def validate_inputs(self, butter_mass_kg: Optional[Decimal] = None, batch_size: Optional[Decimal] = None,
                        butter_yield_factor: Optional[Decimal] = None, **kwargs) -> None:
        if butter_mass_kg is None and batch_size is None:
            raise ValidationError('Provide butter_mass_kg or batch_size')

    def compute(self, butter_mass_kg: Optional[Decimal] = None, batch_size: Optional[Decimal] = None,
                butter_yield_factor: Optional[Decimal] = None, **kwargs) -> CalculatorResult:
        # simple conversion: ghee ~ butter * factor (fat concentration)
        factor = Decimal(butter_yield_factor) if butter_yield_factor is not None else Decimal('0.92')
        if butter_mass_kg is None:
            if batch_size is None:
                raise CalculationError('Insufficient inputs')
            # assume batch_size is milk and some fixed extraction to butter available elsewhere; keep simple
            butter_mass = Decimal(batch_size) * Decimal('0.045')
        else:
            butter_mass = Decimal(butter_mass_kg)

        ghee_mass = (butter_mass * factor).quantize(Decimal('0.0001'))
        data = {'ghee_mass_kg': float(ghee_mass)}
        data['result_summary'] = build_result_summary(data)
        return CalculatorResult(success=True, data=data)
