from decimal import Decimal

from calculators.paneer_yield import PaneerYieldCalculator
from services.json_store import JsonStore
from models.milk_composition import MilkComposition


def test_paneer_yield_from_type():
    repo = JsonStore()
    calc = PaneerYieldCalculator(repository=repo)
    res = calc.run(feed_milk_type='cow', batch_size=Decimal('1000'))
    assert res.success
    data = res.data
    assert data['paneer_mass_kg'] > 0
    assert data['whey_volume_l'] > 0


def test_paneer_yield_from_composition():
    repo = JsonStore()
    calc = PaneerYieldCalculator(repository=repo)
    mc = MilkComposition(fat_pct='4.0', snf_pct='8.7')
    res = calc.run(feed_milk=mc, batch_size=Decimal('500'))
    assert res.success
    assert 'paneer_mass_kg' in res.data
