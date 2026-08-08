from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.product import Product
from models.utility import Utility
from models.milk_composition import MilkComposition
from .repository import Repository
from models.exceptions import DataNotFoundError


class JsonStore(Repository):
    def __init__(self, config_dir: str | Path = None):
        self.base = Path(config_dir) if config_dir else Path(__file__).parent.parent / 'database' / 'config'
        self._products: Dict[str, Product] = {}
        self._milk: Dict[str, MilkComposition] = {}
        self._utilities: Dict[str, Utility] = {}
        self._standards: Dict[str, Any] = {}
        self._load_all()

    def _load_json(self, fname: str):
        path = self.base / fname
        if not path.exists():
            raise DataNotFoundError(f'Config file not found: {path}')
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)

    def _load_all(self):
        # load products
        prod_data = self._load_json('products.json')
        for p in prod_data.get('products', []):
            prod = Product(
                id=p['id'],
                name=p['name'],
                category=p.get('category'),
                unit=p.get('unit', 'kg'),
                default_yield_factor=p.get('default_yield_factor', 1),
                cost_per_unit=p.get('cost_per_unit', 0),
            )
            self._products[prod.id] = prod

        # load milk compositions
        milk_data = self._load_json('milk_properties.json')
        for name, comp in milk_data.get('milk_types', {}).items():
            mc = MilkComposition(fat_pct=comp['fat_pct'], snf_pct=comp['snf_pct'], density=comp.get('density'))
            self._milk[name] = mc

        # load utilities
        util_data = self._load_json('utility_data.json')
        for u in util_data.get('utilities', []):
            util = Utility(name=u['name'], unit=u.get('unit', 'kWh'), cost_per_unit=u.get('cost_per_unit', 0), consumption_per_batch=u.get('consumption_per_batch', 0))
            self._utilities[util.name] = util

        # load standards
        self._standards = self._load_json('standards.json')

    # Repository implementation
    def list_products(self) -> List[Product]:
        return list(self._products.values())

    def get_product(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)

    def get_milk_composition(self, milk_type: str) -> Optional[MilkComposition]:
        return self._milk.get(milk_type)

    def list_utilities(self) -> List[Utility]:
        return list(self._utilities.values())

    def get_utility(self, name: str) -> Optional[Utility]:
        return self._utilities.get(name)

    def get_standard(self, key: str):
        return self._standards.get(key)
