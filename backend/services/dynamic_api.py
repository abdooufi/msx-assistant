"""
Dynamic API caller with Redis caching.
"""
import httpx, json, re
from typing import Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

HEADERS_POST = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Content-Type": "application/json; charset=utf-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.msx.om",
    "Referer": "https://www.msx.om/snapshot.aspx",
}
HEADERS_GET = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.msx.om/",
}


def _substitute(template: Any, symbol: str) -> Any:
    if isinstance(template, str):
        return template.replace('{Symbol}', symbol.upper()).replace('{symbol}', symbol.lower()).replace('{SYMBOL}', symbol.upper())
    if isinstance(template, dict): return {k: _substitute(v, symbol) for k, v in template.items()}
    if isinstance(template, list): return [_substitute(i, symbol) for i in template]
    return template


def _unwrap(data: Any) -> Any:
    if isinstance(data, dict) and "d" in data:
        inner = data["d"]
        if isinstance(inner, str):
            try: return json.loads(inner)
            except: return inner
        return inner
    return data


def _ep_get(ep, key, default=None):
    """Get a field from either an ORM model or a plain dict."""
    if isinstance(ep, dict):
        return ep.get(key, default)
    return getattr(ep, key, default)


async def call_endpoint(ep, symbol: str = "") -> Optional[Any]:
    url     = _substitute(_ep_get(ep, 'url',     ''),        symbol)
    method  = (_ep_get(ep, 'method',  'GET') or 'GET').upper()
    body    = _ep_get(ep, 'body')
    extra   = _ep_get(ep, 'headers') or {}
    ep_name = _ep_get(ep, 'name',    'endpoint')

    body    = _substitute(body, symbol) if body else None
    headers = {**(HEADERS_POST if method == "POST" else HEADERS_GET), **extra}

    # Check cache first
    from cache import get_msx_cache, set_msx_cache, TTL
    cache_key = re.sub(r'[^a-z0-9]', '_', ep_name.lower())[:30]
    cached    = await get_msx_cache(cache_key, symbol)
    if cached is not None:
        print(f"💾 Cache HIT: {ep_name} / {symbol}")
        return cached

    print(f"🌐 {method} {url}" + (f" | body={json.dumps(body)}" if body else ""))

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as c:
            r = await c.post(url, json=body, headers=headers) if method == "POST" else await c.get(url, headers=headers)
            print(f"   → {r.status_code} len={len(r.text)}")
            if r.status_code != 200 or not r.text.strip():
                return None
            try: data = _unwrap(r.json())
            except: data = r.text[:2000]

            # Cache the result
            ttl = TTL.get(cache_key, TTL["default"])
            await set_msx_cache(cache_key, symbol, data)
            return data
    except Exception as e:
        print(f"⚠️ {e}")
        return None


def _match_keywords(message: str, keywords_en: List[str], keywords_ar: List[str]) -> bool:
    msg = message.lower()
    for kw in (keywords_en or []):
        if kw.lower().strip() and kw.lower().strip() in msg: return True
    for kw in (keywords_ar or []):
        if kw.strip() and kw.strip() in message: return True
    return False


async def get_matched_endpoints(db: AsyncSession, message: str) -> List:
    from models import ApiEndpoint
    result = await db.execute(select(ApiEndpoint).where(ApiEndpoint.is_active == True))
    return [ep for ep in result.scalars().all()
            if _match_keywords(message, ep.keywords_en or [], ep.keywords_ar or [])]


async def fetch_dynamic_data(db: AsyncSession, message: str, symbol: str) -> Optional[str]:
    endpoints = await get_matched_endpoints(db, message)
    if not endpoints:
        return None

    print(f"✅ {len(endpoints)} endpoint(s) matched")
    import asyncio
    results = await asyncio.gather(*[call_endpoint(ep, symbol) for ep in endpoints], return_exceptions=True)

    parts = [f"📡 Live Data for {symbol.upper()} from MSX.om:\n"]
    has_data = False
    for ep, result in zip(endpoints, results):
        if result and not isinstance(result, Exception):
            has_data = True
            parts.append(f"🔹 {ep.name}:")
            parts.extend(_format_result(result)[:25])
            parts.append("")
    return "\n".join(parts) if has_data else None


def _safe(v) -> Optional[str]:
    if v is None: return None
    s = str(v).strip()
    if not s or s in ('None','null','0','','-'): return None
    if '${' in s or 'AnswerValue' in s: return None
    return s[:300]


def _format_result(data: Any, depth: int = 0) -> List[str]:
    lines = []
    if depth > 3 or data is None: return lines
    if isinstance(data, dict):
        for k, v in list(data.items())[:30]:
            sub = _format_result(v, depth+1)
            if sub: lines.append(f"{'  '*depth}  • {k}:"); lines.extend(sub)
            else:
                s = _safe(v)
                if s: lines.append(f"{'  '*depth}  • {k}: {s}")
    elif isinstance(data, list):
        for i, item in enumerate(data[:5]):
            lines.append(f"{'  '*depth}  [{i+1}]")
            lines.extend(_format_result(item, depth+1))
    else:
        s = _safe(data)
        if s: lines.append(f"{'  '*depth}  {s}")
    return lines


async def fetch_dynamic_data_with_parser(db: AsyncSession, message: str, symbol: str) -> Optional[str]:
    """
    Same as fetch_dynamic_data but uses msx_parser for company snapshots.
    """
    endpoints = await get_matched_endpoints(db, message)
    if not endpoints:
        return None

    print(f"✅ {len(endpoints)} endpoint(s) matched")
    import asyncio
    from services.msx_parser import format_snapshot_for_ai, flatten_any

    results = await asyncio.gather(
        *[call_endpoint(ep, symbol) for ep in endpoints],
        return_exceptions=True
    )

    parts    = [f"📡 Live Data for {symbol.upper()} from MSX.om:\n"]
    has_data = False

    for ep, result in zip(endpoints, results):
        if result and not isinstance(result, Exception):
            has_data = True
            # Use structured parser for company snapshot
            if 'company' in ep.name.lower() or 'snapshot' in ep.url.lower():
                parts.append(format_snapshot_for_ai(symbol, result))
            else:
                parts.append(f"🔹 {ep.name}:")
                parts.extend(flatten_any(result)[:25])
            parts.append("")

    return "\n".join(parts) if has_data else None
