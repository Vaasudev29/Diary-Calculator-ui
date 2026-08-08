from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

from .exceptions import ValidationError


@dataclass
class ProductionCost:
    material_cost: Decimal = field(default_factory=lambda: Decimal('0'))
    utility_cost: Decimal = field(default_factory=lambda: Decimal('0'))
    labor_cost: Decimal = field(default_factory=lambda: Decimal('0'))
    overhead: Decimal = field(default_factory=lambda: Decimal('0'))
    total_cost: Optional[Decimal] = None

    def __post_init__(self) -> None:
        try:
            self.material_cost = Decimal(self.material_cost)
            self.utility_cost = Decimal(self.utility_cost)
            self.labor_cost = Decimal(self.labor_cost)
            self.overhead = Decimal(self.overhead)
        except (InvalidOperation, TypeError):
            raise ValidationError('cost fields must be numeric')

        for name, val in (('material_cost', self.material_cost), ('utility_cost', self.utility_cost), ('labor_cost', self.labor_cost), ('overhead', self.overhead)):
            if val < 0:
                raise ValidationError(f'{name} must be non-negative', field=name)

        if self.total_cost is None:
            self.total_cost = self.compute_total()

    def compute_total(self) -> Decimal:
        return self.material_cost + self.utility_cost + self.labor_cost + self.overhead
