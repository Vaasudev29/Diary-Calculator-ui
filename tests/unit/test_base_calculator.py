from decimal import Decimal

from calculators.base_calculator import BaseCalculator
from models.result import CalculatorResult
from models.exceptions import ValidationError


class DummyCalculator(BaseCalculator):
    def validate_inputs(self, x: Decimal = None, **kwargs) -> None:
        if x is None:
            raise ValidationError('x is required', field='x')
        if Decimal(x) < 0:
            raise ValidationError('x must be non-negative', field='x')

    def compute(self, x: Decimal = 0, **kwargs) -> CalculatorResult:
        val = Decimal(x) * 2
        return CalculatorResult(success=True, data={'out': val})


def test_dummy_calculator_success():
    c = DummyCalculator()
    res = c.run(x=3)
    assert isinstance(res, CalculatorResult)
    assert res.success
    assert res.data['out'] == 6


def test_dummy_calculator_validation_error():
    c = DummyCalculator()
    res = c.run(x=-1)
    assert not res.success
    assert res.errors is not None
