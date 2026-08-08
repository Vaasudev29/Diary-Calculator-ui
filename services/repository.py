from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from models.product import Product
from models.milk_composition import MilkComposition
from models.utility import Utility


class Repository(ABC):
    """Repository interface for accessing engineering constants and product data."""

    @abstractmethod
    def list_products(self) -> List[Product]:
        pass

    @abstractmethod
    def get_product(self, product_id: str) -> Optional[Product]:
        pass

    @abstractmethod
    def get_milk_composition(self, milk_type: str) -> Optional[MilkComposition]:
        pass

    @abstractmethod
    def list_utilities(self) -> List[Utility]:
        pass

    @abstractmethod
    def get_utility(self, name: str) -> Optional[Utility]:
        pass

    @abstractmethod
    def get_standard(self, key: str):
        pass
