import pytest
from decimal import Decimal

from services.json_store import JsonStore

from calculators.milk_standardization import MilkStandardizationCalculator
from calculators.paneer_yield import PaneerYieldCalculator
from calculators.cheese_yield_detailed import DetailedCheeseYieldCalculator
from calculators.cheese_yield import CheeseYieldCalculator
from calculators.butter_calculator import ButterCalculator
from calculators.ghee_calculator import GheeCalculator
from calculators.ice_cream_mix import IceCreamMixCalculator
from calculators.production_cost import ProductionCostCalculator
from models.result_summary import ResultSummary
from models.ingredient import Ingredient
from models.utility import Utility
from models.batch import Batch


@pytest.mark.integration
def test_calculators_produce_valid_result_summary():
    repo = JsonStore()

    # milk standardization
    mcalc = MilkStandardizationCalculator(repository=repo)
    res = mcalc.run(feed_milk_type='cow', desired_fat_pct=Decimal('4.0'), batch_size=Decimal('1000'))
    assert res.success
    rs = res.data.get('result_summary')
    assert isinstance(rs, dict)
    ResultSummary(**rs)

    # paneer
    pcalc = PaneerYieldCalculator(repository=repo)
    res = pcalc.run(feed_milk_type='cow', batch_size=Decimal('1000'))
    assert res.success
    rs = res.data.get('result_summary')
    assert isinstance(rs, dict)
    ResultSummary(**rs)

    # detailed cheese
    dcalc = DetailedCheeseYieldCalculator(repository=repo)
    res = dcalc.run(feed_milk_type='cow', batch_size=Decimal('1000'), target_moisture_pct=Decimal('45'))
    assert res.success
    rs = res.data.get('result_summary')
    assert isinstance(rs, dict)
    ResultSummary(**rs)

    # simple cheese
    ccalc = CheeseYieldCalculator(repository=repo)
    res = ccalc.run(feed_milk_type='cow', batch_size=Decimal('1000'))
    assert res.success
    rs = res.data.get('result_summary')
    assert isinstance(rs, dict)
    ResultSummary(**rs)

    # butter
    bcalc = ButterCalculator(repository=repo)
    res = bcalc.run(feed_milk_type='cow', batch_size=Decimal('1000'))
    assert res.success
    rs = res.data.get('result_summary')
    assert isinstance(rs, dict)
    ResultSummary(**rs)

    # ghee
    gcalc = GheeCalculator(repository=repo)
    res = gcalc.run(butter_mass_kg=Decimal('10'))
    assert res.success
    rs = res.data.get('result_summary')
    assert isinstance(rs, dict)
    ResultSummary(**rs)

    # ice cream
    ic = IceCreamMixCalculator()
    res = ic.run(batch_size=Decimal('1000'), target_fat_pct=Decimal('10'), target_snf_pct=Decimal('12'))
    assert res.success
    rs = res.data.get('result_summary')
    assert isinstance(rs, dict)
    ResultSummary(**rs)

    # production cost - requires batch
    milk = repo.get_product('Milk')
    ing = Ingredient(product=milk, quantity=Decimal('100'))
    util = Utility(name='Electricity', unit='kWh', cost_per_unit=Decimal('0.12'), consumption_per_batch=Decimal('10'))
    batch = Batch(id='b1', product=repo.get_product('Cheese') or repo.get_product('Paneer'), input_materials=[ing], utilities=[util], batch_size=Decimal('100'))
    pc_calc = ProductionCostCalculator()
    res = pc_calc.run(batch=batch, labor_cost=Decimal('5'), overhead=Decimal('2'))
    assert res.success
    # production cost returns data as ProductionCost and metadata contains result_summary
    rs = res.metadata.get('result_summary') if hasattr(res, 'metadata') else None
    assert isinstance(rs, dict)
    ResultSummary(**rs)
