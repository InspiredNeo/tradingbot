"""
Lightweight caching system for Market Terminal.
- Memory cache: instant, cleared on restart
- Disk cache: survives tab switches, auto-expires, size-limited
"""
import os
import json
import time
import hashlib
import shutil
from pathlib import Path

CACHE_DIR = os.path.expanduser("~/tradingbot/.cache")
MAX_CACHE_SIZE_MB = 50  # never exceed 50MB
DEFAULT_TTL = 900  # 15 minutes


def _cache_key(key):
    return hashlib.md5(key.encode()).hexdigest()


def _cache_path(key):
    return os.path.join(CACHE_DIR, f"{_cache_key(key)}.json")


def _ensure_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_size_mb():
    total = 0
    try:
        for f in Path(CACHE_DIR).glob("*.json"):
            total += f.stat().st_size
    except Exception:
        pass
    return total / (1024 * 1024)


def _evict_oldest():
    """Remove oldest cache files until under size limit."""
    try:
        files = sorted(Path(CACHE_DIR).glob("*.json"), key=lambda f: f.stat().st_mtime)
        while _cache_size_mb() > MAX_CACHE_SIZE_MB and files:
            files.pop(0).unlink()
    except Exception:
        pass


def cache_get(key, ttl=DEFAULT_TTL):
    """Get from cache. Returns None if missing or expired."""
    try:
        path = _cache_path(key)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            entry = json.load(f)
        if time.time() - entry["ts"] > ttl:
            os.unlink(path)  # delete expired
            return None
        return entry["data"]
    except Exception:
        return None


def cache_set(key, data, ttl=DEFAULT_TTL):
    """Save to cache."""
    try:
        _ensure_dir()
        # Clean expired files first
        cache_clean()
        # Check size limit
        if _cache_size_mb() > MAX_CACHE_SIZE_MB:
            _evict_oldest()
        path = _cache_path(key)
        with open(path, "w") as f:
            json.dump({"ts": time.time(), "ttl": ttl, "data": data}, f)
    except Exception:
        pass


def cache_clean():
    """Delete all expired cache files."""
    try:
        _ensure_dir()
        now = time.time()
        deleted = 0
        for f in Path(CACHE_DIR).glob("*.json"):
            try:
                with open(f) as fp:
                    entry = json.load(fp)
                if now - entry["ts"] > entry.get("ttl", DEFAULT_TTL):
                    f.unlink()
                    deleted += 1
            except Exception:
                f.unlink()  # corrupt file, delete it
                deleted += 1
        return deleted
    except Exception:
        return 0


def cache_clear_all():
    """Wipe entire cache — called on app restart."""
    try:
        if os.path.exists(CACHE_DIR):
            shutil.rmtree(CACHE_DIR)
        os.makedirs(CACHE_DIR, exist_ok=True)
    except Exception:
        pass


def cache_info():
    """Return cache stats."""
    try:
        _ensure_dir()
        files = list(Path(CACHE_DIR).glob("*.json"))
        return {
            "files": len(files),
            "size_mb": round(_cache_size_mb(), 2),
            "max_mb": MAX_CACHE_SIZE_MB,
        }
    except Exception:
        return {"files": 0, "size_mb": 0, "max_mb": MAX_CACHE_SIZE_MB}


# In-memory cache (fastest, cleared on restart)
_mem_cache = {}


def mem_get(key, ttl=DEFAULT_TTL):
    entry = _mem_cache.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > ttl:
        del _mem_cache[key]
        return None
    return entry["data"]


def mem_set(key, data):
    _mem_cache[key] = {"ts": time.time(), "data": data}


def mem_clear():
    _mem_cache.clear()
