from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any

from .exceptions import ValidationError


@dataclass
class ResultSummary:
    mass: Optional[Decimal] = None
    net_total_cost: Optional[Decimal] = None
    cost_per_kg: Optional[Decimal] = None
    yield_pct: Optional[float] = None
    extras: Dict[str, Any] = None

    def __post_init__(self) -> None:
        # validate numeric fields if present
        try:
            if self.mass is not None:
                self.mass = Decimal(self.mass)
            if self.net_total_cost is not None:
                self.net_total_cost = Decimal(self.net_total_cost)
            if self.cost_per_kg is not None:
                self.cost_per_kg = Decimal(self.cost_per_kg)
            if self.yield_pct is not None:
                self.yield_pct = float(self.yield_pct)
        except (InvalidOperation, TypeError) as e:
            raise ValidationError(f'ResultSummary numeric fields must be numeric: {e}')

        if self.mass is not None and self.mass < 0:
            raise ValidationError('mass must be non-negative')
        if self.net_total_cost is not None and self.net_total_cost < 0:
            raise ValidationError('net_total_cost must be non-negative')
        if self.cost_per_kg is not None and self.cost_per_kg < 0:
            raise ValidationError('cost_per_kg must be non-negative')
        if self.yield_pct is not None and not (0 <= self.yield_pct <= 100):
            raise ValidationError('yield_pct must be between 0 and 100')

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Convert Decimal to float for JSON serialization
        if d.get('mass') is not None:
            d['mass'] = float(d['mass'])
        if d.get('net_total_cost') is not None:
            d['net_total_cost'] = float(d['net_total_cost'])
        if d.get('cost_per_kg') is not None:
            d['cost_per_kg'] = float(d['cost_per_kg'])
        return d
