from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.milk_composition import MilkComposition
from models.exceptions import ValidationError, CalculationError
from utils.result_helpers import build_result_summary


class ButterCalculator(BaseCalculator):
    """Compute butter yield from cream or milk using butterfat extraction factor.

    Inputs:
      - feed_milk or cream_fat_pct
      - batch_size (L or kg)
      - optionally butterfat_extraction factor

    Outputs:
      - butter_mass_kg, final_volume_l
    """

    def validate_inputs(self, feed_milk: Optional[MilkComposition] = None, feed_milk_type: Optional[str] = None, cream_fat_pct: Optional[Decimal] = None,
                        batch_size: Optional[Decimal] = None, butterfat_extraction: Optional[Decimal] = None, **kwargs) -> None:
        if feed_milk is None and feed_milk_type is None and cream_fat_pct is None:
            raise ValidationError('Provide feed_milk, feed_milk_type, or cream_fat_pct')
        try:
            b = Decimal(batch_size)
        except Exception:
            raise ValidationError('batch_size must be numeric')
        if b <= 0:
            raise ValidationError('batch_size must be positive')

    def compute(self, feed_milk: Optional[MilkComposition] = None, feed_milk_type: Optional[str] = None, cream_fat_pct: Optional[Decimal] = None,
                batch_size: Decimal = None, butterfat_extraction: Optional[Decimal] = None, **kwargs) -> CalculatorResult:
        V = Decimal(batch_size)
        standards = self.repository.get_standard('butter') if self.repository else {}
        if not standards:
            standards = getattr(self.repository, '_standards', {}).get('butter', {}) if self.repository else {}

        extraction = Decimal(butterfat_extraction) if butterfat_extraction is not None else Decimal(standards.get('butterfat_extraction', 0.045))

        # Determine feed fat
        if feed_milk is None and feed_milk_type is not None:
            if not self.repository:
                raise CalculationError('Repository required to resolve feed_milk_type')
            feed_milk = self.repository.get_milk_composition(feed_milk_type)
            if feed_milk is None:
                raise CalculationError(f'Milk type not found: {feed_milk_type}')

        if feed_milk is not None:
            fat_pct = Decimal(feed_milk.fat_pct) / Decimal('100')
        else:
            fat_pct = Decimal(cream_fat_pct) / Decimal('100')

        # butter mass = V * fat_pct * extraction
        butter_mass = (V * fat_pct * extraction).quantize(Decimal('0.0001'))

        data: Dict[str, Any] = {
            'butter_mass_kg': float(butter_mass),
            'feed_fat_pct': float(fat_pct * 100)
        }
        data['result_summary'] = build_result_summary(data)
        return CalculatorResult(success=True, data=data)
