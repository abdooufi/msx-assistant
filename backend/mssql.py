"""
MSSQL connection for MSX website database (MSM_GEO_Live).
Read-only access to securities and historical price data.
"""
import pyodbc
from typing import Optional, List, Dict
from config import get_settings

settings = get_settings()


_ODBC_DRIVERS = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "ODBC Driver 13 for SQL Server",
    "SQL Server",
]


def get_mssql_connection():
    s = settings
    last_err = None
    for driver in _ODBC_DRIVERS:
        try:
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={s.mssql_server},{s.mssql_port};"
                f"DATABASE={s.mssql_database};"
                f"UID={s.mssql_username};"
                f"PWD={s.mssql_password};"
                f"TrustServerCertificate=yes;"
                f"Encrypt=yes;"
            )
            return pyodbc.connect(conn_str, timeout=10)
        except pyodbc.Error as e:
            last_err = e
    raise last_err


def test_mssql_connection() -> tuple[bool, str]:
    """Returns (ok, message)."""
    try:
        conn = get_mssql_connection()
        conn.close()
        return True, "connected"
    except Exception as e:
        msg = str(e).splitlines()[0]  # first line is the most useful part
        return False, msg


def search_companies(query: str, limit: int = 20) -> List[Dict]:
    """
    Search securities by:
    Symbol, LongNameEn, LongNameAr, ShortNameEn, ShortNameAr
    """
    try:
        conn = get_mssql_connection()
        cursor = conn.cursor()
        like_q = f"%{query}%"
        cursor.execute(f"""
            SELECT TOP ({limit})
                [SecurityID],
                [Symbol],
                [LongNameAr],
                [LongNameEn],
                [ShortNameAr],
                [ShortNameEn],
                [type],
                [SectorID],
                [MarketID],
                [StatusID],
                [isin_cd],
                [IPOPrice],
                [isSharia],
                [symbolindex]
            FROM [MSM_GEO_Live].[dbo].[securities]
            WHERE [is_visible] = 1
              AND (
                  [Symbol]      LIKE ?
               OR [LongNameEn]  LIKE ?
               OR [LongNameAr]  LIKE ?
               OR [ShortNameEn] LIKE ?
               OR [ShortNameAr] LIKE ?
              )
            ORDER BY
                CASE WHEN [Symbol] = ? THEN 0 ELSE 1 END,
                [symbolindex]
        """, like_q, like_q, like_q, like_q, like_q, query.upper())

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"⚠️ MSSQL search_companies error: {e}")
        return []


def get_company_by_symbol(symbol: str) -> Optional[Dict]:
    """Get exact company by symbol."""
    results = search_companies(symbol, limit=1)
    return results[0] if results else None


def get_all_companies(limit: int = 500) -> List[Dict]:
    try:
        conn = get_mssql_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT TOP ({limit})
                [SecurityID],
                [Symbol],
                [LongNameAr],
                [LongNameEn],
                [ShortNameAr],
                [ShortNameEn],
                [type],
                [SectorID],
                [MarketID],
                [StatusID],
                [IPOPrice],
                [isSharia],
                [symbolindex]
            FROM [MSM_GEO_Live].[dbo].[securities]
            WHERE [is_visible] = 1
            ORDER BY [symbolindex], [Symbol]
        """)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"⚠️ MSSQL get_all_companies error: {e}")
        return []


def get_historical_prices(
    symbol: str,
    duration: str = "M",
    from_date: str = "2024-01-01",
    to_date: str = "2025-12-31"
) -> List[Dict]:
    """Call BI_GetIndicesSummary stored procedure."""
    try:
        conn = get_mssql_connection()
        cursor = conn.cursor()
        cursor.execute(
            "EXEC BI_GetIndicesSummary @p_duration=?, @p_fromdt=?, @p_todt=?, @p_symbol=?",
            duration, from_date, to_date, symbol.upper()
        )
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        results = []
        for row in rows:
            item = {}
            for col, val in zip(columns, row):
                if hasattr(val, 'isoformat'):
                    item[col] = val.isoformat()
                elif val is not None:
                    item[col] = str(val) if not isinstance(val, (int, float, str, bool)) else val
                else:
                    item[col] = None
            results.append(item)
        return results
    except Exception as e:
        print(f"⚠️ MSSQL get_historical_prices error: {e}")
        return []


def get_latest_price(symbol: str) -> Optional[Dict]:
    from datetime import datetime, timedelta
    today = datetime.now().strftime("%Y-%m-%d")
    one_month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    prices = get_historical_prices(symbol, "D", one_month_ago, today)
    return prices[-1] if prices else None
