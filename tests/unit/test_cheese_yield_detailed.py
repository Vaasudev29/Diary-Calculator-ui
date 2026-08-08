from decimal import Decimal

from services.json_store import JsonStore
from calculators.cheese_yield_detailed import DetailedCheeseYieldCalculator


def test_detailed_cheese_yield():
    repo = JsonStore()
    calc = DetailedCheeseYieldCalculator(repository=repo)
    # Use cow milk 1000 L, target moisture 45%
    res = calc.run(feed_milk_type='cow', batch_size=Decimal('1000'), target_moisture_pct=Decimal('45'))
    assert res.success
    data = res.data
    assert data['cheese_mass_kg'] > 0
    assert data['whey_volume_l'] >= 0
