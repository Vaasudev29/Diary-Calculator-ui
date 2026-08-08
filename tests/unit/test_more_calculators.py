from decimal import Decimal

from services.json_store import JsonStore
from calculators.cheese_yield import CheeseYieldCalculator
from calculators.butter_calculator import ButterCalculator
from calculators.ghee_calculator import GheeCalculator
from calculators.ice_cream_mix import IceCreamMixCalculator
from calculators.packaging_calculator import PackagingCalculator
from calculators.production_cost import ProductionCostCalculator
from calculators.profit_calculator import ProfitCalculator
from models.production_cost import ProductionCost


def test_cheese_yield():
    repo = JsonStore()
    calc = CheeseYieldCalculator(repository=repo)
    res = calc.run(feed_milk_type='cow', batch_size=Decimal('1000'))
    assert res.success
    assert res.data['cheese_mass_kg'] > 0


def test_butter_and_ghee():
    repo = JsonStore()
    bcalc = ButterCalculator(repository=repo)
    res = bcalc.run(feed_milk_type='cow', batch_size=Decimal('1000'))
    assert res.success
    butter = res.data['butter_mass_kg']
    gcalc = GheeCalculator()
    gres = gcalc.run(butter_mass_kg=Decimal(butter))
    assert gres.success


def test_ice_cream_mix():
    ic = IceCreamMixCalculator()
    res = ic.run(batch_size=Decimal('1000'), target_fat_pct=Decimal('10'), target_snf_pct=Decimal('12'))
    assert res.success
    assert 'milk_volume_l' in res.data


def test_packaging_and_profit():
    pack = PackagingCalculator()
    pres = pack.run(production_quantity=Decimal('100'), package_size=Decimal('1'), package_cost_per_unit=Decimal('0.5'))
    assert pres.success
    prod_cost = ProductionCost(material_cost=Decimal('100'), utility_cost=Decimal('10'), labor_cost=Decimal('5'), overhead=Decimal('2'))
    profit_calc = ProfitCalculator()
    r = profit_calc.run(production_cost=prod_cost, revenue=Decimal('200'))
    assert r.success
    assert r.data['profit'] == float(Decimal('200') - prod_cost.total_cost)
