import pytest
from decimal import Decimal

from models.product import Product
from models.milk_composition import MilkComposition
from models.ingredient import Ingredient
from models.utility import Utility
from models.batch import Batch
from models.production_cost import ProductionCost
from models.exceptions import ValidationError


def test_product_validation():
    p = Product(id='milk', name='Milk', unit='L', default_yield_factor=1, cost_per_unit='40')
    assert p.id == 'milk'
    assert isinstance(p.cost_per_unit, Decimal)

    with pytest.raises(ValidationError):
        Product(id='', name='NoID')


def test_milk_composition_validation():
    mc = MilkComposition(fat_pct='3.5', snf_pct=8.5)
    assert mc.fat_pct == Decimal('3.5')

    with pytest.raises(ValidationError):
        MilkComposition(fat_pct=-1, snf_pct=5)


def test_ingredient_and_batch():
    p = Product(id='paneer', name='Paneer', unit='kg', cost_per_unit='350')
    ing = Ingredient(product=p, quantity='10')
    util = Utility(name='Electricity', unit='kWh', cost_per_unit='0.12', consumption_per_batch='50')
    batch = Batch(id='b1', product=p, input_materials=[ing], utilities=[util], batch_size='10')
    assert batch.batch_size == Decimal('10')


def test_production_cost_compute():
    pc = ProductionCost(material_cost='100', utility_cost='10', labor_cost='20', overhead='5')
    assert pc.total_cost == Decimal('135')
