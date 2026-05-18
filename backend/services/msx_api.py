"""
MSX.om Real API Client with Redis caching.
"""
import httpx
import json
from typing import Optional, Any

BASE = "https://www.msx.om"

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


def _unwrap(data: Any) -> Any:
    if isinstance(data, dict) and "d" in data:
        inner = data["d"]
        if isinstance(inner, str):
            try: return json.loads(inner)
            except: return inner
        return inner
    return data


async def _post(path: str, body: dict) -> Optional[Any]:
    url = f"{BASE}/{path}"
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as c:
            r = await c.post(url, json=body, headers=HEADERS_POST)
            print(f"  POST {url} → {r.status_code}")
            if r.status_code == 200 and r.text.strip():
                try: return _unwrap(r.json())
                except: return r.text
    except Exception as e:
        print(f"  ⚠️ POST error: {e}")
    return None


async def _get(url: str) -> Optional[Any]:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as c:
            r = await c.get(url, headers=HEADERS_GET)
            print(f"  GET {url} → {r.status_code}")
            if r.status_code == 200 and r.text.strip():
                try: return _unwrap(r.json())
                except: return r.text
    except Exception as e:
        print(f"  ⚠️ GET error: {e}")
    return None


# ─── Cached API calls ─────────────────────────────────────────────

async def _cached_post(cache_key: str, path: str, body: dict) -> Optional[Any]:
    from cache import get_msx_cache, set_msx_cache
    symbol = body.get("Symbol", "")
    cached = await get_msx_cache(cache_key, symbol)
    if cached is not None:
        return cached
    data = await _post(path, body)
    if data:
        await set_msx_cache(cache_key, symbol, data)
    return data


async def _cached_get(cache_key: str, symbol: str, url: str) -> Optional[Any]:
    from cache import get_msx_cache, set_msx_cache
    cached = await get_msx_cache(cache_key, symbol)
    if cached is not None:
        return cached
    data = await _get(url)
    if data:
        await set_msx_cache(cache_key, symbol, data)
    return data


# ─── Public API functions ─────────────────────────────────────────

async def get_company_info(symbol: str):
    return await _cached_post("company", "snapshot.aspx/company", {"Symbol": symbol.upper()})

async def get_snap_news(symbol: str):
    return await _cached_post("news", "snapshot.aspx/SnapNews", {"Symbol": symbol.upper()})

async def get_snap_last20_trades(symbol: str):
    return await _cached_post("last20trades", "snapshot.aspx/SnapLast20trades", {"Symbol": symbol.upper()})

async def get_snap_last4_years(symbol: str):
    return await _cached_post("last4years", "snapshot.aspx/SnapLast4years", {"Symbol": symbol.upper()})

async def get_snap_financial(symbol: str):
    return await _cached_post("financial", "snapshot.aspx/SnapFinancial", {"Symbol": symbol.upper()})

async def get_dividends(symbol: str):
    return await _cached_post("dividends", "snapshot.aspx/DividendDistributionReports", {"Symbol": symbol.upper()})

async def get_chart_data(symbol: str, period: str = "1m"):
    return await _cached_post(f"chart", "snapshot.aspx/CompanyChartData",
                               {"Symbol": symbol.upper(), "Period": period})

async def get_company_news(symbol: str, year: int = 2026):
    return await _cached_get("news", symbol,
                              f"{BASE}/company-news.aspx?s={symbol.lower()}&y={year}&f=1&t=5&i=")

async def get_bod_members(symbol: str):
    return await _cached_get("board", symbol,
                              f"{BASE}/BODMembersSnap.aspx?s={symbol.lower()}")

async def get_subsidiaries(symbol: str):
    return await _cached_get("subsidiaries", symbol,
                              f"{BASE}/SubsidiariesandAssociatesSnap.aspx?s={symbol.lower()}")

async def get_chart_data_get(symbol: str):
    return await _cached_get("chart", symbol,
                              f"{BASE}/company-chart-data.aspx?t=true&s={symbol.lower()}")

async def get_sustainability(symbol: str, year: int = 2025, report_type: str = "E"):
    return await _cached_post("governance", "snapshot.aspx/SustainabilityReports",
                               {"Symbol": symbol.upper(), "Year": str(year), "Type": report_type})

async def get_governance(symbol: str, year: int = 2025):
    return await _cached_post("governance", "snapshot.aspx/CorporateGovernanceReport",
                               {"Symbol": symbol.upper(), "Year": str(year), "Type": "CGR"})


async def fetch_all_company_data(symbol: str) -> dict:
    import asyncio
    sym = symbol.upper()
    print(f"🌐 Fetching all MSX.om data for {sym}...")
    results = await asyncio.gather(
        get_company_info(sym), get_snap_last4_years(sym),
        get_snap_news(sym), get_dividends(sym),
        get_snap_financial(sym), get_snap_last20_trades(sym),
        return_exceptions=True
    )
    keys = ["company", "last4years", "news", "dividends", "financial", "last20trades"]
    data = {}
    for key, result in zip(keys, results):
        if result and not isinstance(result, Exception):
            data[key] = result
            print(f"  ✅ {key}")
        else:
            print(f"  ⚠️ {key}: no data")
    return data


async def get_ownership_data(symbol: str) -> Optional[Any]:
    """
    POST snapshot.aspx/SnapOwnership or similar endpoint
    for Non-Omani / GCC / Arab / Foreign ownership breakdown.
    """
    # Try multiple possible endpoints for ownership
    endpoints = [
        ("snapshot.aspx/SnapOwnership",        {"Symbol": symbol.upper()}),
        ("snapshot.aspx/SnapShareholderData",   {"Symbol": symbol.upper()}),
        ("snapshot.aspx/OwnershipData",         {"Symbol": symbol.upper()}),
        ("snapshot.aspx/SnapInvestorData",      {"Symbol": symbol.upper()}),
    ]
    for path, body in endpoints:
        data = await _post(path, body)
        if data:
            print(f"  ✅ Ownership data from {path}")
            return data
    return None


async def get_snap_major_shareholders(symbol: str) -> Optional[Any]:
    """POST snapshot.aspx/SnapMajorShareholders"""
    return await _post("snapshot.aspx/SnapMajorShareholders", {"Symbol": symbol.upper()})


async def get_snap_ownership_structure(symbol: str) -> Optional[Any]:
    """
    Fetch ownership structure including:
    Non-Omani %, GCC %, Arab %, Foreign %
    from the snapshot page data.
    """
    # The ownership data is often embedded in the main company snapshot
    # or in a separate ownership endpoint
    results = await asyncio.gather(
        _post("snapshot.aspx/SnapOwnership",          {"Symbol": symbol.upper()}),
        _post("snapshot.aspx/SnapShareholders",        {"Symbol": symbol.upper()}),
        _post("snapshot.aspx/SnapMajorShareholders",   {"Symbol": symbol.upper()}),
        _post("snapshot.aspx/InvestorDetails",         {"Symbol": symbol.upper()}),
        return_exceptions=True
    )
    for r in results:
        if r and not isinstance(r, Exception):
            return r
    return None
