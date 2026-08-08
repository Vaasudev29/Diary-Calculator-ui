from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .exceptions import ValidationError


@dataclass
class MilkComposition:
    fat_pct: Decimal
    snf_pct: Decimal
    protein_pct: Decimal | None = None
    lactose_pct: Decimal | None = None
    density: Decimal | None = None

    def __post_init__(self) -> None:
        try:
            self.fat_pct = Decimal(self.fat_pct)
            self.snf_pct = Decimal(self.snf_pct)
            if self.protein_pct is not None:
                self.protein_pct = Decimal(self.protein_pct)
            if self.lactose_pct is not None:
                self.lactose_pct = Decimal(self.lactose_pct)
            if self.density is not None:
                self.density = Decimal(self.density)
        except (InvalidOperation, TypeError):
            raise ValidationError('Composition values must be numeric')

        if not (0 <= self.fat_pct <= 100):
            raise ValidationError('fat_pct must be between 0 and 100', field='fat_pct')
        if not (0 <= self.snf_pct <= 100):
            raise ValidationError('snf_pct must be between 0 and 100', field='snf_pct')
        if self.protein_pct is not None and not (0 <= self.protein_pct <= 100):
            raise ValidationError('protein_pct must be between 0 and 100', field='protein_pct')
        if self.lactose_pct is not None and not (0 <= self.lactose_pct <= 100):
            raise ValidationError('lactose_pct must be between 0 and 100', field='lactose_pct')
