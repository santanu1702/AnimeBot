"""
storage.py
Lightweight JSON-file persistence layer.

For a bot of this scope a full database is overkill — everything the
admin panel needs (user list, scan counter, enabled flag, error log)
is small enough to live in a couple of JSON files. Swap this module
out for Redis/Postgres later without touching the handlers, since
everything is accessed through the functions below.
"""

import json
import os
import time
from threading import Lock

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
LOGS_FILE = os.path.join(DATA_DIR, "logs.json")

_lock = Lock()


def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save(path, data):
    with _lock:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)


# ---------------------------------------------------------------- users ----
def add_user(user_id: int, username: str | None = None):
    users = _load(USERS_FILE, {})
    key = str(user_id)
    if key not in users:
        users[key] = {
            "username": username,
            "joined": time.time(),
        }
        _save(USERS_FILE, users)
    return users


def get_all_users() -> list[int]:
    users = _load(USERS_FILE, {})
    return [int(uid) for uid in users.keys()]


def total_users() -> int:
    return len(_load(USERS_FILE, {}))


# ---------------------------------------------------------------- stats ----
def _default_stats():
    return {
        "total_scans": 0,
        "successful_scans": 0,
        "failed_scans": 0,
        "started_at": time.time(),
        "bot_enabled": True,
    }


def get_stats() -> dict:
    stats = _load(STATS_FILE, None)
    if stats is None:
        stats = _default_stats()
        _save(STATS_FILE, stats)
    return stats


def bump_stat(key: str, amount: int = 1):
    stats = get_stats()
    stats[key] = stats.get(key, 0) + amount
    _save(STATS_FILE, stats)
    return stats


def set_bot_enabled(enabled: bool):
    stats = get_stats()
    stats["bot_enabled"] = enabled
    _save(STATS_FILE, stats)


def is_bot_enabled() -> bool:
    return get_stats().get("bot_enabled", True)


def uptime_seconds() -> float:
    return time.time() - get_stats().get("started_at", time.time())


# ----------------------------------------------------------------- logs ----
MAX_LOGS = 200


def add_log(message: str, level: str = "INFO"):
    logs = _load(LOGS_FILE, [])
    logs.append(
        {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "message": message,
        }
    )
    logs = logs[-MAX_LOGS:]
    _save(LOGS_FILE, logs)


def get_logs(limit: int = 20) -> list[dict]:
    logs = _load(LOGS_FILE, [])
    return logs[-limit:]
