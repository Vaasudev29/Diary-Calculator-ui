from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else Path('data') / 'settings.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({'theme': 'light'})

    def _read(self) -> Dict[str, Any]:
        with self.path.open('r', encoding='utf-8') as f:
            return json.load(f)

    def _write(self, data: Dict[str, Any]) -> None:
        with self.path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        data = self._read()
        return data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self._read()
        data[key] = value
        self._write(data)
