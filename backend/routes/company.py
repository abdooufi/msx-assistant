from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta
from auth import get_current_admin
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(prefix="/api/companies", tags=["companies"])
_executor = ThreadPoolExecutor(max_workers=4)


def _run_sync(func, *args):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(_executor, func, *args)


@router.get("")
async def list_companies(
    search: Optional[str] = None,
    _: str = Depends(get_current_admin),
):
    """List all companies from MSSQL securities table."""
    try:
        from mssql import search_companies, get_all_companies
        if search:
            data = await _run_sync(search_companies, search)
        else:
            data = await _run_sync(get_all_companies)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MSSQL error: {str(e)}")


@router.get("/search")
async def search_companies_endpoint(
    q: str = Query(..., min_length=1),
    _: str = Depends(get_current_admin),
):
    """Search companies by symbol or name."""
    try:
        from mssql import search_companies
        data = await _run_sync(search_companies, q)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MSSQL error: {str(e)}")


@router.get("/lookup/{symbol}")
async def lookup_company(symbol: str):
    """Public endpoint - get company info + latest prices."""
    try:
        from mssql import get_company_by_symbol, get_latest_price
        company = await _run_sync(get_company_by_symbol, symbol.upper())
        latest = await _run_sync(get_latest_price, symbol.upper())
        return {
            "symbol": symbol.upper(),
            "company": company,
            "latest_price": latest,
            "msx_url": f"https://www.msx.om/snapshot.aspx?s={symbol.upper()}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MSSQL error: {str(e)}")


@router.get("/prices/{symbol}")
async def get_prices(
    symbol: str,
    duration: str = Query("M", regex="^[DWMY]$"),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    _: str = Depends(get_current_admin),
):
    """
    Get historical prices via BI_GetIndicesSummary stored procedure.
    duration: D=Daily, W=Weekly, M=Monthly, Y=Yearly
    """
    try:
        from mssql import get_historical_prices
        today = datetime.now().strftime("%Y-%m-%d")
        default_from = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        data = await _run_sync(
            get_historical_prices,
            symbol.upper(),
            duration,
            from_date or default_from,
            to_date or today
        )
        return {
            "symbol": symbol.upper(),
            "duration": duration,
            "from": from_date or default_from,
            "to": to_date or today,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MSSQL error: {str(e)}")


@router.get("/health")
async def mssql_health(_: str = Depends(get_current_admin)):
    """Test MSSQL connection."""
    try:
        from mssql import test_mssql_connection
        ok, msg = await _run_sync(test_mssql_connection)
        return {"mssql": "connected" if ok else "failed", "detail": msg}
    except Exception as e:
        return {"mssql": "failed", "detail": str(e)}


# ─── MSX.om API endpoints ─────────────────────────────────────────

@router.get("/snapshot/{symbol}")
async def get_company_snapshot(symbol: str):
    """Get full company snapshot from all MSX.om APIs."""
    from services.msx_api import fetch_all_company_data, format_for_ai
    data = await fetch_all_company_data(symbol.upper())
    return {"symbol": symbol.upper(), "data": data}


@router.get("/news/{symbol}")
async def get_company_news_endpoint(symbol: str, year: int = 2026):
    """Get company news from MSX.om."""
    from services.msx_api import get_company_news
    data = await get_company_news(symbol.upper(), year)
    return {"symbol": symbol.upper(), "year": year, "news": data}


@router.get("/chart/{symbol}")
async def get_company_chart(symbol: str, period: str = "1m"):
    """
    Get chart data from MSX.om.
    period: 1w, 1m, 3m, 6m, 1y, 5y
    """
    from services.msx_api import get_chart_data, get_chart_data_get
    data = await get_chart_data(symbol.upper(), period)
    if not data:
        data = await get_chart_data_get(symbol.upper())
    return {"symbol": symbol.upper(), "period": period, "chart": data}


@router.get("/dividends/{symbol}")
async def get_company_dividends(symbol: str):
    """Get dividend history from MSX.om."""
    from services.msx_api import get_dividends
    data = await get_dividends(symbol.upper())
    return {"symbol": symbol.upper(), "dividends": data}


@router.get("/financial/{symbol}")
async def get_company_financial(symbol: str):
    """Get financial statements from MSX.om."""
    from services.msx_api import get_snap_financial
    data = await get_snap_financial(symbol.upper())
    return {"symbol": symbol.upper(), "financial": data}


@router.get("/board/{symbol}")
async def get_board_members(symbol: str):
    """Get board of directors from MSX.om."""
    from services.msx_api import get_bod_members
    data = await get_bod_members(symbol.upper())
    return {"symbol": symbol.upper(), "board": data}
