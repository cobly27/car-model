"""Persistent update history."""

import json
from datetime import datetime

from .config import UPDATE_HISTORY_PATH

MAX_HISTORY_ITEMS = 80


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def load_update_history():
    if not UPDATE_HISTORY_PATH.exists():
        return []
    try:
        with UPDATE_HISTORY_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def save_update_history(items):
    with UPDATE_HISTORY_PATH.open("w", encoding="utf-8") as f:
        json.dump(items[:MAX_HISTORY_ITEMS], f, ensure_ascii=False, indent=2)


def append_update_history(item):
    history = load_update_history()
    history.insert(0, item)
    save_update_history(history)
    return item
