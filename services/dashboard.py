from __future__ import annotations

from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime


def compute_cheese_kpis(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute KPI metrics for cheese production from history records.

    Expects history records to contain at least:
      - timestamp (ISO str)
      - type == 'cheese_production'
      - result_summary with keys: cheese_mass_kg, net_total_cost (or similar)
    """
    # filter cheese records
    cheese_records = [r for r in history if r.get('type') == 'cheese_production' and r.get('result_summary')]
    if not cheese_records:
        return {
            'total_batches': 0,
            'total_cheese_kg': 0.0,
            'total_net_cost': 0.0,
            'avg_cost_per_kg': None,
            'recent': []
        }

    rows: List[Dict[str, Any]] = []
    total_cheese = Decimal('0')
    total_net_cost = Decimal('0')
    for r in cheese_records:
        ts = r.get('timestamp')
        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            dt = datetime.utcnow()
        rs = r.get('result_summary', {})
        cheese_mass = Decimal(str(rs.get('cheese_mass_kg') or 0))
        net_cost = Decimal(str(rs.get('net_total_cost') or 0))
        total_cheese += cheese_mass
        total_net_cost += net_cost
        rows.append({'timestamp': dt, 'cheese_mass_kg': float(cheese_mass), 'net_total_cost': float(net_cost)})

    total_batches = len(rows)
    total_cheese_f = float(total_cheese)
    total_net_cost_f = float(total_net_cost)
    avg_cost_per_kg = float(total_net_cost / total_cheese) if total_cheese > 0 else None

    # sort recent by timestamp descending
    recent_sorted = sorted(rows, key=lambda x: x['timestamp'], reverse=True)
    # convert timestamps to ISO strings for serialization
    for item in recent_sorted:
        if isinstance(item['timestamp'], datetime):
            item['timestamp'] = item['timestamp'].isoformat()

    return {
        'total_batches': total_batches,
        'total_cheese_kg': total_cheese_f,
        'total_net_cost': total_net_cost_f,
        'avg_cost_per_kg': avg_cost_per_kg,
        'recent': recent_sorted
    }


def build_timeseries_df(history: List[Dict[str, Any]], metric: str = 'net_total_cost') -> List[Dict[str, Any]]:
    cheese_records = [r for r in history if r.get('type') == 'cheese_production' and r.get('result_summary')]
    rows: List[Dict[str, Any]] = []
    for r in cheese_records:
        ts = r.get('timestamp')
        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            dt = datetime.utcnow()
        rs = r.get('result_summary', {})
        val = rs.get('net_total_cost') if metric == 'net_total_cost' else rs.get('cheese_mass_kg')
        rows.append({'timestamp': dt, metric: float(val or 0)})
    # sort by timestamp
    rows_sorted = sorted(rows, key=lambda x: x['timestamp'])
    return rows_sorted
