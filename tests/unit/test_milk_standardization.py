from decimal import Decimal

from calculators.milk_standardization import MilkStandardizationCalculator
from services.json_store import JsonStore
from models.milk_composition import MilkComposition


def test_add_cream_scenario():
    repo = JsonStore()
    calc = MilkStandardizationCalculator(repository=repo)
    # cow milk 3.5% to target 4.5% for 1000 L
    res = calc.run(feed_milk_type='cow', desired_fat_pct=Decimal('4.5'), batch_size=Decimal('1000'))
    assert res.success
    data = res.data
    assert data['action'] == 'add_cream'
    assert data['added_volume_l'] > 0


def test_add_skim_scenario():
    repo = JsonStore()
    calc = MilkStandardizationCalculator(repository=repo)
    # cow milk 3.5% to target 3.0% for 1000 L -> dilute with skim
    res = calc.run(feed_milk_type='cow', desired_fat_pct=Decimal('3.0'), batch_size=Decimal('1000'))
    assert res.success
    data = res.data
    assert data['action'] == 'add_skim'
    assert data['added_volume_l'] > 0


def test_feed_composition_input():
    repo = JsonStore()
    calc = MilkStandardizationCalculator(repository=repo)
    mc = MilkComposition(fat_pct='3.0', snf_pct='8.5')
    res = calc.run(feed_milk=mc, desired_fat_pct=Decimal('4.0'), batch_size=Decimal('500'))
    assert res.success
    assert res.data['action'] == 'add_cream'
