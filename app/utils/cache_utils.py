import hashlib
import json
import os
import time
from typing import Any, Optional

from app.config import CACHE_DIR, CACHE_TTL_HOURS

_CACHE_TTL_SECONDS = max(0.0, CACHE_TTL_HOURS) * 60 * 60


def _cache_path(namespace: str, key: str) -> str:
    safe_namespace = "".join(ch for ch in namespace if ch.isalnum() or ch in {"_", "-"})
    digest = hashlib.sha256(str(key).encode("utf-8")).hexdigest()
    folder = os.path.join(CACHE_DIR, safe_namespace or "default")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{digest}.json")


def cache_get(namespace: str, key: str) -> Optional[Any]:
    path = _cache_path(namespace, key)
    try:
        if _CACHE_TTL_SECONDS <= 0:
            return None
        if time.time() - os.path.getmtime(path) > _CACHE_TTL_SECONDS:
            return None
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def cache_set(namespace: str, key: str, value: Any) -> None:
    path = _cache_path(namespace, key)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2)
