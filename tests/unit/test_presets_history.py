import tempfile
from pathlib import Path
from services.presets import PresetStore, HistoryStore


def test_preset_save_load(tmp_path):
    pfile = tmp_path / 'presets.json'
    store = PresetStore(path=pfile)
    store.save_preset('test1', {'a': 1})
    assert 'test1' in store.list_presets()
    p = store.get_preset('test1')
    assert p['a'] == 1
    store.delete_preset('test1')
    assert 'test1' not in store.list_presets()


def test_history_append_and_list(tmp_path):
    hfile = tmp_path / 'history.json'
    hs = HistoryStore(path=hfile)
    hs.append({'type': 't1', 'value': 10})
    hs.append({'type': 't2', 'value': 20})
    allh = hs.list_history()
    assert len(allh) == 2
    recent = hs.list_history(limit=1)
    assert len(recent) == 1
