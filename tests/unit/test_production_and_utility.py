from decimal import Decimal

from services.json_store import JsonStore
from calculators.production_cost import ProductionCostCalculator
from calculators.utility_calculator import UtilityCalculator
from models.product import Product
from models.ingredient import Ingredient
from models.utility import Utility
from models.batch import Batch


def make_sample_batch():
    repo = JsonStore()
    milk = repo.get_product('Milk')
    paneer = repo.get_product('Paneer')
    ing = Ingredient(product=milk, quantity=Decimal('100'))
    util = Utility(name='Electricity', unit='kWh', cost_per_unit=Decimal('0.12'), consumption_per_batch=Decimal('10'))
    batch = Batch(id='b1', product=paneer, input_materials=[ing], utilities=[util], batch_size=Decimal('100'))
    return batch


def test_production_cost_calculator():
    batch = make_sample_batch()
    calc = ProductionCostCalculator()
    res = calc.run(batch=batch, labor_cost=Decimal('5'), overhead=Decimal('2'))
    assert res.success
    pc = res.data
    assert pc.material_cost >= 0
    assert pc.utility_cost >= 0
    assert pc.total_cost == pc.compute_total()


def test_utility_calculator():
    batch = make_sample_batch()
    calc = UtilityCalculator()
    res = calc.run(batch=batch)
    assert res.success
    data = res.data
    assert 'breakdown' in data and len(data['breakdown']) == 1
    assert data['total_utility_cost'] >= 0
