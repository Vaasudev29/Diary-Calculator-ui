from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from .exceptions import ValidationError


@dataclass
class Utility:
    name: str
    unit: str = 'kWh'
    cost_per_unit: Decimal = field(default_factory=lambda: Decimal('0'))
    consumption_per_batch: Decimal = field(default_factory=lambda: Decimal('0'))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValidationError('Utility name must be provided', field='name')
        try:
            self.cost_per_unit = Decimal(self.cost_per_unit)
            self.consumption_per_batch = Decimal(self.consumption_per_batch)
        except (InvalidOperation, TypeError):
            raise ValidationError('cost and consumption must be numeric')

        if self.cost_per_unit < 0:
            raise ValidationError('cost_per_unit must be non-negative', field='cost_per_unit')
        if self.consumption_per_batch < 0:
            raise ValidationError('consumption_per_batch must be non-negative', field='consumption_per_batch')
