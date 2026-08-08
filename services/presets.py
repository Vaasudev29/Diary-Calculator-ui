from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class PresetStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else Path('data') / 'presets.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({'presets': {}})

    def _read(self) -> Dict[str, Any]:
        with self.path.open('r', encoding='utf-8') as f:
            return json.load(f)

    def _write(self, data: Dict[str, Any]) -> None:
        with self.path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    def list_presets(self) -> List[str]:
        data = self._read()
        return list(data.get('presets', {}).keys())

    def get_preset(self, name: str) -> Optional[Dict[str, Any]]:
        data = self._read()
        return data.get('presets', {}).get(name)

    def save_preset(self, name: str, payload: Dict[str, Any]) -> None:
        data = self._read()
        data.setdefault('presets', {})[name] = payload
        self._write(data)

    def delete_preset(self, name: str) -> None:
        data = self._read()
        if name in data.get('presets', {}):
            del data['presets'][name]
            self._write(data)


class HistoryStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else Path('data') / 'history.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({'history': []})

    def _read(self) -> Dict[str, Any]:
        with self.path.open('r', encoding='utf-8') as f:
            return json.load(f)

    def _write(self, data: Dict[str, Any]) -> None:
        with self.path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    def append(self, record: Dict[str, Any]) -> None:
        data = self._read()
        record = dict(record)
        record['timestamp'] = datetime.utcnow().isoformat()
        data.setdefault('history', []).append(record)
        self._write(data)

    def list_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        data = self._read()
        hist = data.get('history', [])
        if limit:
            return hist[-limit:][::-1]
        return hist[::-1]

    # convenience method to migrate into SQL store
    def to_sql_store(self, sql_store):
        data = self._read()
        for r in data.get('history', []):
            sql_store.append_history(r)
