from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.milk_composition import MilkComposition
from models.exceptions import ValidationError, CalculationError
from utils.result_helpers import build_result_summary


class CheeseYieldCalculator(BaseCalculator):
    """Simple cheese yield calculator based on coagulation yield factor.

    Inputs:
      - feed_milk or feed_milk_type
      - batch_size (L)
      - optional coagulation_yield_factor override

    Outputs:
      - cheese_mass_kg, whey_volume_l, yield_pct
    """

    def validate_inputs(self, feed_milk: Optional[MilkComposition] = None, feed_milk_type: Optional[str] = None,
                        batch_size: Optional[Decimal] = None, coagulation_yield_factor: Optional[Decimal] = None, **kwargs) -> None:
        if feed_milk is None and feed_milk_type is None:
            raise ValidationError('Either feed_milk or feed_milk_type must be provided')
        try:
            b = Decimal(batch_size)
        except Exception:
            raise ValidationError('batch_size must be numeric')
        if b <= 0:
            raise ValidationError('batch_size must be positive')

    def compute(self, feed_milk: Optional[MilkComposition] = None, feed_milk_type: Optional[str] = None,
                batch_size: Decimal = None, coagulation_yield_factor: Optional[Decimal] = None, **kwargs) -> CalculatorResult:
        if feed_milk is None:
            if not self.repository:
                raise CalculationError('Repository required to resolve feed_milk_type')
            feed_milk = self.repository.get_milk_composition(feed_milk_type)
            if feed_milk is None:
                raise CalculationError(f'Milk type not found: {feed_milk_type}')

        V = Decimal(batch_size)
        standards = self.repository.get_standard('cheese') if self.repository else {}
        if not standards:
            # try fallback
            standards = getattr(self.repository, '_standards', {}).get('cheese', {}) if self.repository else {}

        cf = Decimal(coagulation_yield_factor) if coagulation_yield_factor is not None else Decimal(standards.get('coagulation_yield_factor', 0.1))
        whey_pct = Decimal(standards.get('whey_loss_pct', 0.9))

        if cf <= 0 or cf >= 1:
            raise CalculationError('Invalid coagulation_yield_factor')

        cheese_mass = (V * cf).quantize(Decimal('0.0001'))
        whey_volume = (V * whey_pct).quantize(Decimal('0.0001'))
        yield_pct = (cheese_mass / V * Decimal('100')).quantize(Decimal('0.01'))

        data: Dict[str, Any] = {
            'cheese_mass_kg': float(cheese_mass),
            'whey_volume_l': float(whey_volume),
            'yield_pct': float(yield_pct)
        }
        data['result_summary'] = build_result_summary(data)
        return CalculatorResult(success=True, data=data)
