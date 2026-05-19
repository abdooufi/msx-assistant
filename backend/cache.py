"""
Redis cache for MSX API responses.
Reduces repeated calls to MSX.om and MSSQL.
Falls back gracefully if Redis is not available.
"""
import redis.asyncio as aioredis
import json
import hashlib
from typing import Optional, Any
from config import get_settings

settings = get_settings()

# Global Redis client
_redis: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """Get Redis connection, return None if unavailable."""
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await _redis.ping()
            print(f"✅ Redis connected: {settings.redis_url}")
        except Exception as e:
            print(f"⚠️ Redis unavailable ({e}) — caching disabled")
            _redis = None
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        print("🔌 Redis connection closed")


# ─── TTL settings (seconds) ──────────────────────────────────────

TTL = {
    "company":      300,   # 5 min  — live price changes
    "news":         600,   # 10 min — news updates
    "financial":    3600,  # 1 hour — financials rarely change
    "dividends":    3600,  # 1 hour
    "last4years":   3600,  # 1 hour
    "last20trades":  60,    # 1 min  — trades update frequently
    "notifications":    60,   # 1 min  — special trades/news update frequently
    "special_trades": 60,    # 1 min  — today's special trades (intraday)
    "chart":        300,   # 5 min
    "board":        86400, # 1 day  — board members rarely change
    "subsidiaries": 86400, # 1 day
    "governance":   86400, # 1 day
    "mssql":        300,   # 5 min  — MSSQL price data
    "default":      300,   # 5 min
}


def _make_key(prefix: str, symbol: str, extra: str = "") -> str:
    """Build cache key: msx:{prefix}:{symbol}:{extra}"""
    parts = ["msx", prefix, symbol.upper()]
    if extra:
        parts.append(extra)
    return ":".join(parts)


def _hash_key(data: str) -> str:
    """Hash long keys."""
    return hashlib.md5(data.encode()).hexdigest()[:12]


# ─── Core cache operations ────────────────────────────────────────

async def cache_get(key: str) -> Optional[Any]:
    """Get value from cache. Returns None if not found or Redis unavailable."""
    r = await get_redis()
    if not r:
        return None
    try:
        val = await r.get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        print(f"⚠️ Cache GET error: {e}")
    return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Store value in cache with TTL. Returns True if successful."""
    r = await get_redis()
    if not r:
        return False
    try:
        await r.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        print(f"⚠️ Cache SET error: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Delete a cache key."""
    r = await get_redis()
    if not r:
        return False
    try:
        await r.delete(key)
        return True
    except Exception:
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching pattern. Returns count deleted."""
    r = await get_redis()
    if not r:
        return 0
    try:
        keys = await r.keys(pattern)
        if keys:
            return await r.delete(*keys)
    except Exception:
        pass
    return 0


# ─── Convenience wrappers ─────────────────────────────────────────

async def get_msx_cache(endpoint_name: str, symbol: str, extra: str = "") -> Optional[Any]:
    """Get cached MSX API response."""
    key = _make_key(endpoint_name, symbol, extra)
    data = await cache_get(key)
    if data is not None:
        print(f"💾 Cache HIT: {key}")
    return data


async def set_msx_cache(endpoint_name: str, symbol: str, value: Any, extra: str = "") -> bool:
    """Cache an MSX API response with appropriate TTL."""
    key  = _make_key(endpoint_name, symbol, extra)
    ttl  = TTL.get(endpoint_name, TTL["default"])
    ok   = await cache_set(key, value, ttl)
    if ok:
        print(f"💾 Cache SET: {key} (TTL={ttl}s)")
    return ok


async def invalidate_symbol(symbol: str) -> int:
    """Clear all cached data for a symbol."""
    count = await cache_delete_pattern(f"msx:*:{symbol.upper()}*")
    print(f"🗑️ Cleared {count} cache entries for {symbol}")
    return count


async def get_cache_stats() -> dict:
    """Get Redis memory and key stats."""
    r = await get_redis()
    if not r:
        return {"status": "unavailable"}
    try:
        info   = await r.info("memory")
        keys   = await r.dbsize()
        msx_keys = len(await r.keys("msx:*"))
        return {
            "status":          "connected",
            "total_keys":      keys,
            "msx_keys":        msx_keys,
            "used_memory":     info.get("used_memory_human", "?"),
            "peak_memory":     info.get("used_memory_peak_human", "?"),
            "maxmemory":       info.get("maxmemory_human", "unlimited"),
            "eviction_policy": info.get("maxmemory_policy", "noeviction"),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
