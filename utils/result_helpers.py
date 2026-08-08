"""Helper utilities to build standardized result summaries across calculators."""
from __future__ import annotations

from typing import Dict, Any, Optional
from decimal import Decimal
from models.result_summary import ResultSummary
from models.exceptions import ValidationError


def extract_mass_from_data(data: Dict[str, Any]) -> Optional[float]:
    # look for common mass keys
    for key in ('cheese_mass_kg', 'paneer_mass_kg', 'butter_mass_kg', 'ghee_mass_kg', 'mass', 'quantity'):
        if key in data and data.get(key) is not None:
            try:
                return float(data.get(key))
            except Exception:
                continue
    return None


def extract_net_cost_from_data(data: Dict[str, Any]) -> Optional[float]:
    # look for common cost keys
    for key in ('net_total_cost', 'total_cost', 'net_cost', 'cost'):
        if key in data and data.get(key) is not None:
            try:
                return float(data.get(key))
            except Exception:
                continue
    return None


def build_result_summary(data: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a harmonized result_summary dict with keys mass, net_total_cost, cost_per_kg, yield_pct.

    Keeps values numeric where possible.
    """
    summary: Dict[str, Any] = {}
    mass = extract_mass_from_data(data)
    if mass is not None:
        summary['mass'] = mass
    net = extract_net_cost_from_data(data)
    if net is not None:
        summary['net_total_cost'] = net
    if 'yield_pct' in data:
        try:
            summary['yield_pct'] = float(data.get('yield_pct'))
        except Exception:
            pass

    if mass is not None and net is not None and mass != 0:
        try:
            summary['cost_per_kg'] = net / mass
        except Exception:
            pass

    if extra:
        for k, v in extra.items():
            summary.setdefault(k, v)

    # Build ResultSummary dataclass to validate schema
    try:
        rs = ResultSummary(
            mass=summary.get('mass') or summary.get('cheese_mass_kg') or summary.get('paneer_mass_kg') or summary.get('butter_mass_kg') or summary.get('ghee_mass_kg'),
            net_total_cost=summary.get('net_total_cost') or summary.get('total_cost'),
            cost_per_kg=summary.get('cost_per_kg'),
            yield_pct=summary.get('yield_pct'),
            extras={k: v for k, v in summary.items() if k not in ('mass', 'net_total_cost', 'cost_per_kg', 'yield_pct')}
        )
    except ValidationError:
        # if validation fails, return lightweight dict but raise for visibility
        raise

    return rs.to_dict()
