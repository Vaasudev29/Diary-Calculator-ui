from __future__ import annotations

from decimal import Decimal, InvalidOperation, getcontext
from typing import Optional, Dict, Any

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.milk_composition import MilkComposition
from models.exceptions import ValidationError, CalculationError
from utils.result_helpers import build_result_summary


getcontext().prec = 9


class PaneerYieldCalculator(BaseCalculator):
    """Calculate paneer yield from milk based on standard coagulation yields.

    Inputs:
      - feed_milk or feed_milk_type (to lookup composition)
      - batch_size (volume of milk in liters)
      - optionally override coagulation_yield_factor

    Returns CalculatorResult with keys:
      paneer_mass_kg, whey_volume_l, yield_pct, feed_composition, whey_composition
    """

    def validate_inputs(self, feed_milk: Optional[MilkComposition] = None, feed_milk_type: Optional[str] = None,
                        batch_size: Optional[Decimal] = None, coagulation_yield_factor: Optional[Decimal] = None, **kwargs) -> None:
        if feed_milk is None and feed_milk_type is None:
            raise ValidationError('Either feed_milk or feed_milk_type must be provided')
        try:
            b = Decimal(batch_size)
        except (InvalidOperation, TypeError):
            raise ValidationError('batch_size must be numeric')
        if b <= 0:
            raise ValidationError('batch_size must be positive')
        if coagulation_yield_factor is not None:
            try:
                cf = Decimal(coagulation_yield_factor)
            except (InvalidOperation, TypeError):
                raise ValidationError('coagulation_yield_factor must be numeric')
            if cf <= 0 or cf > 1:
                raise ValidationError('coagulation_yield_factor must be between 0 and 1')

    def compute(self, feed_milk: Optional[MilkComposition] = None, feed_milk_type: Optional[str] = None,
                batch_size: Decimal = None, coagulation_yield_factor: Optional[Decimal] = None, **kwargs) -> CalculatorResult:
        # resolve feed milk
        if feed_milk is None:
            if not self.repository:
                raise CalculationError('Repository required to resolve feed_milk_type')
            feed_milk = self.repository.get_milk_composition(feed_milk_type)
            if feed_milk is None:
                raise CalculationError(f'Milk type not found: {feed_milk_type}')

        V = Decimal(batch_size)

        standards = {}
        if self.repository:
            # repository.get_standard may return specific key; JsonStore stores all in _standards
            standards = self.repository.get_standard('paneer') or self.repository._standards.get('paneer', {})

        cf = Decimal(coagulation_yield_factor) if coagulation_yield_factor is not None else Decimal(standards.get('coagulation_yield_factor', 0.18))
        whey_pct = Decimal(standards.get('whey_loss_pct', 0.82))

        if cf <= 0 or cf >= 1:
            raise CalculationError('Invalid coagulation_yield_factor from standards')
        if whey_pct <= 0 or whey_pct >= 1:
            raise CalculationError('Invalid whey_loss_pct from standards')

        # Paneer mass in kg (assume 1 L milk ~ 1 kg for approximations)
        paneer_mass = (V * cf).quantize(Decimal('0.0001'))
        whey_volume = (V * whey_pct).quantize(Decimal('0.0001'))
        yield_pct = (paneer_mass / V * Decimal('100')).quantize(Decimal('0.01'))

        # approximate whey composition: scale feed composition by whey fraction
        try:
            whey_fat = (Decimal(feed_milk.fat_pct) * (whey_volume / V)).quantize(Decimal('0.0001'))
            whey_snf = (Decimal(feed_milk.snf_pct) * (whey_volume / V)).quantize(Decimal('0.0001'))
        except Exception:
            raise CalculationError('Invalid feed milk composition')

        data: Dict[str, Any] = {
            'paneer_mass_kg': float(paneer_mass),
            'whey_volume_l': float(whey_volume),
            'yield_pct': float(yield_pct),
            'feed_composition': {'fat_pct': float(feed_milk.fat_pct), 'snf_pct': float(feed_milk.snf_pct)},
            'whey_composition': {'fat_pct': float(whey_fat), 'snf_pct': float(whey_snf)},
        }

        # add standardized result_summary
        data['result_summary'] = build_result_summary(data)

        return CalculatorResult(success=True, data=data)
