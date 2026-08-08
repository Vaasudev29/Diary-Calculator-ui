from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.exceptions import ValidationError, CalculationError
from utils.result_helpers import build_result_summary


class IceCreamMixCalculator(BaseCalculator):
    """Compute mix formulation for ice cream given desired solids and fat targets.

    This is a simplified example: target mix of milk solids, fat, sugar, stabilizer.
    Inputs:
      - batch_size (L)
      - target_fat_pct
      - target_snf_pct
    Outputs:
      - ingredient quantities (milk, cream, sugar) as example
    """

    def validate_inputs(self, batch_size: Optional[Decimal] = None, target_fat_pct: Optional[Decimal] = None, target_snf_pct: Optional[Decimal] = None, **kwargs) -> None:
        try:
            b = Decimal(batch_size)
        except Exception:
            raise ValidationError('batch_size must be numeric')
        if b <= 0:
            raise ValidationError('batch_size must be positive')
        if target_fat_pct is None or target_snf_pct is None:
            raise ValidationError('target_fat_pct and target_snf_pct are required')

    def compute(self, batch_size: Decimal = None, target_fat_pct: Decimal = None, target_snf_pct: Decimal = None, **kwargs) -> CalculatorResult:
        V = Decimal(batch_size)
        tf = Decimal(target_fat_pct) / Decimal('100')
        ts = Decimal(target_snf_pct) / Decimal('100')

        # naive formulation: use milk at 3.5% fat and cream at 40% fat
        milk_fat = Decimal('0.035')
        cream_fat = Decimal('0.40')

        # solve volumes of milk (Vm) and cream (Vc): (milk_fat*Vm + cream_fat*Vc) / (Vm+Vc) = tf and Vm+Vc = V
        # Vm = V - Vc; substitute: (milk_fat*(V-Vc) + cream_fat*Vc)/V = tf -> Vc*(cream_fat - milk_fat) = V*(tf - milk_fat)
        denom = (cream_fat - milk_fat)
        if denom == 0:
            raise CalculationError('Invalid formulation constants')
        Vc = (V * (tf - milk_fat)) / denom
        Vm = V - Vc

        # sugar to reach solids: assume sugar contributes to SNF; naive sugar needed = V*(ts - milk_snf)
        milk_snf = Decimal('0.086')
        sugar_needed = Decimal('0')
        if ts > milk_snf:
            sugar_needed = V * (ts - milk_snf)

        data: Dict[str, Any] = {
            'milk_volume_l': float(Vm),
            'cream_volume_l': float(Vc),
            'sugar_kg': float(sugar_needed),
            'target_fat_pct': float(tf * 100),
            'target_snf_pct': float(ts * 100)
        }
        # approximate mass of final mix
        final_mass = float(Vm + Vc)
        data['result_summary'] = build_result_summary({'mass': final_mass, **data})
        return CalculatorResult(success=True, data=data)
