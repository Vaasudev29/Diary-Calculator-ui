from decimal import Decimal

from services.calculator_service import CalculatorOrchestrator


def test_orchestrator_produce_cheese():
    orch = CalculatorOrchestrator()
    res = orch.produce_cheese(feed_milk_type='cow', batch_size_l=Decimal('1000'), target_moisture_pct=Decimal('45'), labor_cost=Decimal('10'), overhead=Decimal('5'))
    assert 'yield' in res
    assert 'production_cost' in res
    assert res['production_cost']['gross_total_cost'] >= 0
    # check whey credit fields
    pc = res['production_cost']
    assert 'whey_credit' in pc
    assert 'net_total_cost' in pc
    # whey credit should be computed based on solids or volume
    assert pc['whey_credit'] >= 0
    # cost per kg may be None if cheese_mass zero
    assert pc['cost_per_kg'] is None or pc['cost_per_kg'] >= 0


def test_whey_processing_override_disable():
    orch = CalculatorOrchestrator()
    # disable whey processing per batch
    res = orch.produce_cheese(feed_milk_type='cow', batch_size_l=Decimal('1000'), target_moisture_pct=Decimal('45'), labor_cost=Decimal('10'), overhead=Decimal('5'), whey_processing_overrides={'enabled': False})
    pc = res['production_cost']
    # when disabled, processing cost should be zero (whey_processing_cost field present)
    assert pc['whey_processing_cost'] == 0.0
