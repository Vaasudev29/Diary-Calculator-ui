from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.milk_composition import MilkComposition
from models.exceptions import ValidationError, CalculationError
from utils.result_helpers import build_result_summary


class DetailedCheeseYieldCalculator(BaseCalculator):
    """Detailed cheese yield calculator using component mass-balance.

    Steps:
      - Compute total component masses (fat, protein, lactose, other SNF)
      - Apply retention fractions from standards to determine solids captured in curd
      - Compute cheese mass from captured solids and target moisture
      - Compute whey volumes and compositions
    """

    def validate_inputs(self, feed_milk: Optional[MilkComposition] = None, feed_milk_type: Optional[str] = None,
                        batch_size: Optional[Decimal] = None, target_moisture_pct: Optional[Decimal] = None, **kwargs) -> None:
        if feed_milk is None and feed_milk_type is None:
            raise ValidationError('Provide feed_milk or feed_milk_type')
        try:
            b = Decimal(batch_size)
        except Exception:
            raise ValidationError('batch_size must be numeric')
        if b <= 0:
            raise ValidationError('batch_size must be positive')
        if target_moisture_pct is None:
            raise ValidationError('target_moisture_pct is required')

    def compute(self, feed_milk: Optional[MilkComposition] = None, feed_milk_type: Optional[str] = None,
                batch_size: Decimal = None, target_moisture_pct: Decimal = None, **kwargs) -> CalculatorResult:
        if feed_milk is None:
            if not self.repository:
                raise CalculationError('Repository required to resolve feed_milk_type')
            feed_milk = self.repository.get_milk_composition(feed_milk_type)
            if feed_milk is None:
                raise CalculationError(f'Milk type not found: {feed_milk_type}')

        V = Decimal(batch_size)

        # Standards
        sd = (self.repository.get_standard('cheese_detailed') if self.repository else None) or getattr(self.repository, '_standards', {}).get('cheese_detailed', {})
        protein_ret = Decimal(sd.get('protein_retention', 0.95))
        fat_ret = Decimal(sd.get('fat_retention', 0.95))
        lac_ret = Decimal(sd.get('lactose_retention', 0.1))
        other_ret = Decimal(sd.get('other_snf_retention', 0.25))
        moisture_target = Decimal(target_moisture_pct) / Decimal('100')
        salt_uptake = Decimal(sd.get('salt_uptake_pct', 1.2)) / Decimal('100')

        # Component masses (assume 1 L ~ 1 kg)
        total_fat = Decimal(feed_milk.fat_pct) / Decimal('100') * V
        total_protein = Decimal(feed_milk.protein_pct) / Decimal('100') * V if feed_milk.protein_pct is not None else Decimal('0')
        total_lactose = Decimal(feed_milk.lactose_pct) / Decimal('100') * V if feed_milk.lactose_pct is not None else Decimal('0')
        total_snf = Decimal(feed_milk.snf_pct) / Decimal('100') * V
        # other_snf approximated as SNF - protein - lactose
        other_snf = total_snf - total_protein - total_lactose
        if other_snf < 0:
            other_snf = Decimal('0')

        # Apply retentions
        captured_protein = total_protein * protein_ret
        captured_fat = total_fat * fat_ret
        captured_lactose = total_lactose * lac_ret
        captured_other = other_snf * other_ret

        solids_captured = captured_protein + captured_fat + captured_lactose + captured_other

        # Cheese mass from solids and target moisture: cheese_mass = solids_captured / (1 - moisture_target)
        if moisture_target >= 1 or moisture_target < 0:
            raise CalculationError('Invalid target moisture')
        cheese_mass = (solids_captured / (Decimal('1') - moisture_target)).quantize(Decimal('0.0001'))

        # Salt added based on uptake
        salt_added = cheese_mass * salt_uptake

        # Whey = V - cheese_mass (approx)
        whey_volume = (V - cheese_mass).quantize(Decimal('0.0001'))

        # Whey composition (remaining components)
        whey_fat = (total_fat - captured_fat)
        whey_protein = (total_protein - captured_protein)
        whey_lactose = (total_lactose - captured_lactose)
        whey_other = (other_snf - captured_other)

        data: Dict[str, Any] = {
            'cheese_mass_kg': float(cheese_mass),
            'cheese_solids_kg': float(solids_captured),
            'salt_added_kg': float(salt_added),
            'whey_volume_l': float(whey_volume),
            'whey_composition': {
                'fat_kg': float(whey_fat),
                'protein_kg': float(whey_protein),
                'lactose_kg': float(whey_lactose),
                'other_snf_kg': float(whey_other),
            },
            'retention': {
                'protein_retention': float(protein_ret),
                'fat_retention': float(fat_ret),
                'lactose_retention': float(lac_ret),
                'other_retention': float(other_ret),
            },
            'target_moisture_pct': float(moisture_target * 100)
        }

        # Add standardized summary
        data['result_summary'] = build_result_summary(data)
        return CalculatorResult(success=True, data=data)
