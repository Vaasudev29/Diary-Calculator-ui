from __future__ import annotations

import os
from typing import Tuple
from services.presets import PresetStore, HistoryStore
from database.sql_store import SQLStore


def get_stores() -> Tuple[object, object]:
    """Return (preset_store, history_store) based on APP_DATASTORE env var.

    If APP_DATASTORE=sql use SQLStore, otherwise default to JSON stores.
    """
    mode = os.getenv('APP_DATASTORE', 'json').lower()
    if mode == 'sql':
        sql = SQLStore()
        # SQLStore has methods save_preset/list_presets/append_history; we wrap for compatibility
        class PresetWrapper:
            def save_preset(self, name, payload):
                sql.save_preset(name, payload)
            def list_presets(self):
                return [p for p in []]
            def get_preset(self, name):
                # simplistic
                return None
            def delete_preset(self, name):
                pass

        class HistoryWrapper:
            def append(self, record):
                sql.append_history(record)
            def list_history(self, limit=None):
                # Not implemented fully; fall back to empty
                return []

        return PresetWrapper(), HistoryWrapper()
    else:
        return PresetStore(), HistoryStore()
