from __future__ import annotations

from decimal import Decimal, getcontext, InvalidOperation
from typing import Optional, Dict, Any

from models.milk_composition import MilkComposition
from models.result import CalculatorResult
from models.exceptions import ValidationError, CalculationError
from calculators.base_calculator import BaseCalculator
from utils.result_helpers import build_result_summary


getcontext().prec = 9


class MilkStandardizationCalculator(BaseCalculator):
    """Calculator for milk standardization to reach target fat (and optional SNF).

    This calculator supports two simple operations:
      - Add cream (high-fat) to increase fat
      - Add skim milk (low-fat) to dilute fat

    The repository can provide standard cream/skim fat percentages via standards.
    """

    def validate_inputs(self, feed_milk: Optional[MilkComposition] = None, feed_milk_type: Optional[str] = None,
                        desired_fat_pct: Optional[Decimal] = None, batch_size: Optional[Decimal] = None, **kwargs) -> None:
        if feed_milk is None and feed_milk_type is None:
            raise ValidationError('Either feed_milk or feed_milk_type must be provided')
        if desired_fat_pct is None:
            raise ValidationError('desired_fat_pct is required')
        try:
            desired = Decimal(desired_fat_pct)
        except (InvalidOperation, TypeError):
            raise ValidationError('desired_fat_pct must be numeric')
        if not (Decimal('0') <= desired <= Decimal('100')):
            raise ValidationError('desired_fat_pct must be between 0 and 100')
        try:
            b = Decimal(batch_size)
        except (InvalidOperation, TypeError):
            raise ValidationError('batch_size must be numeric')
        if b <= 0:
            raise ValidationError('batch_size must be positive')

    def compute(self, feed_milk: Optional[MilkComposition] = None, feed_milk_type: Optional[str] = None,
                desired_fat_pct: Decimal = None, batch_size: Decimal = None, **kwargs) -> CalculatorResult:
        # Resolve feed composition
        if feed_milk is None:
            if not self.repository:
                raise CalculationError('No repository configured to look up milk type')
            mc = self.repository.get_milk_composition(feed_milk_type)
            if mc is None:
                raise CalculationError(f'Milk type not found: {feed_milk_type}')
            feed_milk = mc

        try:
            Fm = Decimal(feed_milk.fat_pct) / Decimal('100')
            Fd = Decimal(desired_fat_pct) / Decimal('100')
            V = Decimal(batch_size)
        except Exception as e:
            raise CalculationError(f'Invalid numeric values: {e}')

        standards = {}
        if self.repository:
            standards = self.repository.get_standard('') or self.repository._standards  # fallback
        cream_pct = Decimal(standards.get('cream_fat_pct', 40)) / Decimal('100')
        skim_pct = Decimal(standards.get('skim_fat_pct', 0.5)) / Decimal('100')

        result: Dict[str, Any] = {
            'feed_fat_pct': float(feed_milk.fat_pct),
            'desired_fat_pct': float(desired_fat_pct),
            'batch_size': float(V),
        }

        # No change needed
        if Fm == Fd:
            result.update({'action': 'none', 'added_volume': 0, 'final_volume': float(V)})
            result['result_summary'] = build_result_summary(result)
            return CalculatorResult(success=True, data=result)

        # Increase fat by adding cream
        if Fd > Fm:
            if cream_pct <= Fd:
                raise CalculationError('cream fat percentage must be greater than desired fat')
            # solve Vc = (Fd*V - Fm*V) / (Fc - Fd)
            denom = (cream_pct - Fd)
            if denom == 0:
                raise CalculationError('Denominator zero in cream addition calculation')
            Vc = (Fd * V - Fm * V) / denom
            if Vc < 0:
                raise CalculationError('Calculated cream volume negative')
            final_vol = V + Vc
            result.update({'action': 'add_cream', 'added_volume_l': float(Vc), 'cream_fat_pct': float(cream_pct * 100), 'final_volume_l': float(final_vol)})
            result['result_summary'] = build_result_summary(result)
            return CalculatorResult(success=True, data=result)

        # Decrease fat by adding skim milk (dilution)
        if Fd < Fm:
            # To dilute, skim fat must be lower than desired fat (Fs < Fd)
            if skim_pct < Fd:
                # solve Vs = (Fm*V - Fd*V) / (Fd - Fs)
                denom = (Fd - skim_pct)
                if denom == 0:
                    raise CalculationError('Denominator zero in skim addition calculation')
                Vs = (Fm * V - Fd * V) / denom
                if Vs < 0:
                    raise CalculationError('Calculated skim volume negative')
                final_vol = V + Vs
                result.update({'action': 'add_skim', 'added_volume_l': float(Vs), 'skim_fat_pct': float(skim_pct * 100), 'final_volume_l': float(final_vol)})
                result['result_summary'] = build_result_summary(result)
                return CalculatorResult(success=True, data=result)
            else:
                # If skim fat is higher or equal to desired fat, cannot dilute using skim
                raise CalculationError('Skim milk fat is higher than desired fat; cannot dilute')

        raise CalculationError('Unhandled standardization case')
