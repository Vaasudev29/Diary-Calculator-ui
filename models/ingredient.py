from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

from .product import Product
from .exceptions import ValidationError


@dataclass
class Ingredient:
    product: Product
    quantity: Decimal = field(default_factory=lambda: Decimal('0'))
    unit: str = 'kg'
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.product, Product):
            raise ValidationError('product must be a Product instance', field='product')
        try:
            self.quantity = Decimal(self.quantity)
        except (InvalidOperation, TypeError):
            raise ValidationError('quantity must be numeric', field='quantity')

        if self.quantity < 0:
            raise ValidationError('quantity must be non-negative', field='quantity')
