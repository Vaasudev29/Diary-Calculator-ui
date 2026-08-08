from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import List

from .product import Product
from .ingredient import Ingredient
from .utility import Utility
from .exceptions import ValidationError


@dataclass
class Batch:
    id: str
    product: Product
    input_materials: List[Ingredient]
    utilities: List[Utility]
    batch_size: Decimal = field(default_factory=lambda: Decimal('0'))
    unit: str = 'kg'

    def __post_init__(self) -> None:
        if not self.id:
            raise ValidationError('Batch id must be provided', field='id')
        if not isinstance(self.product, Product):
            raise ValidationError('product must be a Product instance', field='product')
        if not isinstance(self.input_materials, list):
            raise ValidationError('input_materials must be a list', field='input_materials')
        if not isinstance(self.utilities, list):
            raise ValidationError('utilities must be a list', field='utilities')
        try:
            self.batch_size = Decimal(self.batch_size)
        except (InvalidOperation, TypeError):
            raise ValidationError('batch_size must be numeric', field='batch_size')
        if self.batch_size <= 0:
            raise ValidationError('batch_size must be positive', field='batch_size')
