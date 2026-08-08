from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

from .exceptions import ValidationError


@dataclass
class Product:
    id: str
    name: str
    category: Optional[str] = None
    unit: str = 'kg'
    default_yield_factor: Decimal = field(default_factory=lambda: Decimal('1'))
    cost_per_unit: Decimal = field(default_factory=lambda: Decimal('0'))

    def __post_init__(self) -> None:
        if not self.id:
            raise ValidationError('Product id must be provided', field='id')
        if not self.name:
            raise ValidationError('Product name must be provided', field='name')
        try:
            self.default_yield_factor = Decimal(self.default_yield_factor)
        except (InvalidOperation, TypeError):
            raise ValidationError('default_yield_factor must be numeric', field='default_yield_factor')
        try:
            self.cost_per_unit = Decimal(self.cost_per_unit)
        except (InvalidOperation, TypeError):
            raise ValidationError('cost_per_unit must be numeric', field='cost_per_unit')

        if self.default_yield_factor < 0:
            raise ValidationError('default_yield_factor must be non-negative', field='default_yield_factor')
        if self.cost_per_unit < 0:
            raise ValidationError('cost_per_unit must be non-negative', field='cost_per_unit')
