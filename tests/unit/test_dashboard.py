from services.presets import HistoryStore
from services.dashboard import compute_cheese_kpis, build_timeseries_df
from decimal import Decimal
import tempfile
import json


def test_compute_cheese_kpis_and_timeseries(tmp_path):
    hfile = tmp_path / 'history.json'
    hs = HistoryStore(path=hfile)
    # append two records
    hs.append({'type': 'cheese_production', 'result_summary': {'cheese_mass_kg': 100, 'net_total_cost': 500}})
    hs.append({'type': 'cheese_production', 'result_summary': {'cheese_mass_kg': 200, 'net_total_cost': 800}})
    history = hs.list_history()
    kpis = compute_cheese_kpis(history)
    assert kpis['total_batches'] == 2
    assert abs(kpis['total_cheese_kg'] - 300.0) < 1e-6
    assert abs(kpis['total_net_cost'] - 1300.0) < 1e-6
    assert abs(kpis['avg_cost_per_kg'] - (1300.0 / 300.0)) < 1e-6

    ts = build_timeseries_df(history, metric='net_total_cost')
    assert isinstance(ts, list)
    assert len(ts) == 2
