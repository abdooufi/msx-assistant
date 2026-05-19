"""
Company search service - complete pipeline:
1. Detect company from user message
2. Search MSSQL securities table → get official Symbol
3. Fetch live data from MSX.om APIs
4. Get historical prices from MSSQL stored procedure
5. Build clean context for AI
"""
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=4)


def _run_sync(func, *args):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(_executor, func, *args)


def detect_company_query(message: str) -> Optional[str]:
    """
    Extract company symbol or name from user message.
    Returns the cleanest possible search term.
    """
    # 1. Explicit MSX URL
    url_match = re.search(r'[?&]s=([A-Za-z0-9]+)', message, re.IGNORECASE)
    if url_match:
        return url_match.group(1).upper()

    # 2. Uppercase ticker standalone (3-6 chars) — check FIRST before trigger words
    stopwords = {
        'WHAT','WHEN','WHERE','TELL','SHOW','GIVE','FROM','WITH',
        'ABOUT','INFO','THIS','THAT','HAVE','DOES','WILL','YOUR',
        'THEIR','HELP','NEED','WANT','PLEASE','THANK','HELLO','GOOD',
        'LIST','MOST','LAST','NEXT','BEST','MORE','LESS','MANY','THE',
        'SURE','JUST','SOME','MUCH','VERY','ALSO','ONLY','THEN','THAN',
        # Common English words that look like tickers
        'AND','FOR','NOT','ARE','WAS','HAS','HAD','ITS','OUR','ALL',
        'ANY','BUT','CAN','MAY','WHO','HOW','WHY','NEW','OLD','TOP',
        'CEO','COO','CFO','EVP','SVP','INC','LTD','LLC','PLC',
        # Board/management keywords that are not tickers
        'BOARD','CHAIR','VICE','EXEC','DIRECTOR','CHAIRMAN','DEPUTY',
    }
    tickers = re.findall(r'\b([A-Z]{3,6})\b', message)
    for t in tickers:
        if t not in stopwords:
            return t

    # 3. Trigger words → extract company name after them
    # But clean up leading words like "of", "for", "about" etc.
    trigger = re.search(
        r'(?:about|info(?:rmation)?|search|lookup|find|price(?:\s+of)?|stock(?:\s+of)?|'
        r'shares?(?:\s+of)?|company|tell me about|what is|show me|details?|explain|news(?:\s+of)?|'
        r'dividend(?:\s+of)?|financial(?:\s+of)?|chart(?:\s+of)?|trade(?:\s+of)?|report(?:\s+of)?|'
        r'أخبار|سعر|شركة|معلومات|توزيعات|مالية|تداول|رسم)\s+(?:of\s+|for\s+|about\s+)?(.+?)(?:\?|$)',
        message, re.IGNORECASE
    )
    if trigger:
        raw = trigger.group(1).strip()
        # Remove leading "of", "for", "about", "the"
        raw = re.sub(r'^(?:of|for|about|the|on)\s+', '', raw, flags=re.IGNORECASE).strip()
        # If result looks like a ticker (all caps, 3-6 chars), return as-is
        if re.match(r'^[A-Z]{3,6}$', raw):
            return raw
        # Otherwise return the cleaned phrase
        return raw if raw else None

    # 4. Arabic company name patterns
    ar_match = re.search(r'[\u0600-\u06FF\s]{3,}', message)
    if ar_match:
        return ar_match.group(0).strip()

    return None


def _clean_symbol_from_query(query: str) -> str:
    """
    Clean up a query string — remove common English filler words
    that might have been captured with the company name.
    """
    # Remove leading/trailing filler
    filler = r'^(?:of|for|about|the|on|a|an)\s+|\s+(?:company|stock|share|price|info)$'
    cleaned = re.sub(filler, '', query.strip(), flags=re.IGNORECASE).strip()
    return cleaned if cleaned else query


def _detect_duration(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ['daily', 'today', 'day', 'يومي']):    return 'D'
    if any(w in msg for w in ['weekly', 'week', 'أسبوعي']):         return 'W'
    if any(w in msg for w in ['yearly', 'year', 'annual', 'سنوي']): return 'Y'
    return 'M'


def _detect_chart_period(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ['week', '1w', '7 day']):       return '1w'
    if any(w in msg for w in ['3 month', '3m', 'quarter']):  return '3m'
    if any(w in msg for w in ['6 month', '6m', 'half']):     return '6m'
    if any(w in msg for w in ['year', '1y', '12 month']):    return '1y'
    if any(w in msg for w in ['5 year', '5y']):              return '5y'
    return '1m'


# ─── MSSQL ────────────────────────────────────────────────────────

def _mssql_conn():
    import pyodbc
    from config import get_settings
    s = get_settings()
    drivers = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13 for SQL Server",
        "SQL Server",
    ]
    last_err = None
    for driver in drivers:
        try:
            return pyodbc.connect(
                f"DRIVER={{{driver}}};"
                f"SERVER={s.mssql_server},{s.mssql_port};"
                f"DATABASE={s.mssql_database};"
                f"UID={s.mssql_username};PWD={s.mssql_password};"
                f"TrustServerCertificate=yes;Encrypt=yes;",
                timeout=10
            )
        except pyodbc.Error as e:
            last_err = e
    raise last_err


def _search_mssql(query: str) -> Optional[dict]:
    """
    Search securities by Symbol, LongNameEn, LongNameAr, ShortNameEn, ShortNameAr.
    Tries exact symbol match first, then LIKE search.
    """
    try:
        conn = _mssql_conn()
        cursor = conn.cursor()

        # First: exact symbol match
        cursor.execute("""
            SELECT TOP 1
                [SecurityID],[Symbol],[LongNameAr],[LongNameEn],
                [ShortNameAr],[ShortNameEn],[type],[SectorID],
                [MarketID],[StatusID],[isin_cd],[IPOPrice],[isSharia],[symbolindex]
            FROM [MSM_GEO_Live].[dbo].[securities]
            WHERE [is_visible] = 1 AND UPPER([Symbol]) = ?
        """, query.upper())
        row = cursor.fetchone()

        if not row:
            # Second: LIKE search across all name fields
            like_q = f"%{query}%"
            cursor.execute("""
                SELECT TOP 1
                    [SecurityID],[Symbol],[LongNameAr],[LongNameEn],
                    [ShortNameAr],[ShortNameEn],[type],[SectorID],
                    [MarketID],[StatusID],[isin_cd],[IPOPrice],[isSharia],[symbolindex]
                FROM [MSM_GEO_Live].[dbo].[securities]
                WHERE [is_visible] = 1
                  AND ([Symbol] LIKE ? OR [LongNameEn] LIKE ? OR [LongNameAr] LIKE ?
                    OR [ShortNameEn] LIKE ? OR [ShortNameAr] LIKE ?)
                ORDER BY
                    CASE WHEN UPPER([Symbol]) = ? THEN 0 ELSE 1 END,
                    [symbolindex]
            """, like_q, like_q, like_q, like_q, like_q, query.upper())
            row = cursor.fetchone()

        conn.close()
        if row:
            return dict(zip([c[0] for c in cursor.description], row))
        return None
    except Exception as e:
        print(f"⚠️ MSSQL search: {e}")
        return None


def _get_prices(symbol: str, duration: str, from_date: str, to_date: str) -> list:
    try:
        conn = _mssql_conn()
        cursor = conn.cursor()
        cursor.execute(
            "EXEC BI_GetIndicesSummary @p_duration=?, @p_fromdt=?, @p_todt=?, @p_symbol=?",
            duration, from_date, to_date, symbol.upper()
        )
        cols = [c[0] for c in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            item = {}
            for col, val in zip(cols, row):
                if hasattr(val, 'isoformat'): item[col] = val.isoformat()
                elif isinstance(val, (int, float, str, bool, type(None))): item[col] = val
                else: item[col] = str(val)
            result.append(item)
        return result
    except Exception as e:
        print(f"⚠️ MSSQL prices: {e}")
        return []


# ─── Context builder ──────────────────────────────────────────────

def _build_db_section(company: dict) -> str:
    lines = ["📋 Company Details (MSX Database):"]
    fields = {
        'LongNameEn':  'English Name',
        'LongNameAr':  'Arabic Name',
        'ShortNameEn': 'Short Name (EN)',
        'ShortNameAr': 'Short Name (AR)',
        'Symbol':      'Ticker Symbol',
        'isin_cd':     'ISIN Code',
        'IPOPrice':    'IPO Price',
        'isSharia':    'Sharia Compliant',
        'type':        'Security Type',
        'SectorID':    'Sector ID',
        'MarketID':    'Market ID',
    }
    for key, label in fields.items():
        val = company.get(key)
        if val is None or str(val).strip() in ('', 'None', '0'): continue
        if key == 'isSharia': val = 'Yes' if val else 'No'
        lines.append(f"  • {label}: {val}")
    return "\n".join(lines)


def _format_prices(prices: list) -> str:
    if not prices: return ""
    lines = [f"📉 Historical Prices (last {min(5, len(prices))} of {len(prices)} records):"]
    for p in prices[-5:]:
        parts = " | ".join(f"{k}: {v}" for k, v in p.items() if v is not None)
        lines.append(f"  • {parts[:200]}")
    return "\n".join(lines)


# ─── Main entry point ─────────────────────────────────────────────

async def get_company_info(db: AsyncSession, message: str) -> Optional[str]:
    # Step 1: Detect query
    raw_query = detect_company_query(message)
    if not raw_query:
        return None

    # Step 2: Clean the query
    query = _clean_symbol_from_query(raw_query)
    print(f"🔍 Company query: '{query}' (raw: '{raw_query}')")

    # Step 3: Search MSSQL
    company = await _run_sync(_search_mssql, query)

    # Step 4: If not found and query has multiple words, try each word
    if not company and ' ' in query:
        for word in query.split():
            if len(word) >= 3:
                company = await _run_sync(_search_mssql, word)
                if company:
                    print(f"  Found via word: '{word}'")
                    break

    if not company:
        print(f"❌ Not found: '{query}'")
        return None

    symbol  = company.get('Symbol', '').strip()
    name_en = company.get('LongNameEn') or company.get('ShortNameEn') or symbol
    print(f"✅ Found: {symbol} — {name_en}")

    context = [
        f"📊 Company: {name_en} ({symbol})",
        f"🔗 Profile: https://www.msx.om/snapshot.aspx?s={symbol}",
        "",
        _build_db_section(company),
    ]

    # Step 5: Detect what user wants
    msg_lower = message.lower()
    wants_news      = any(w in msg_lower for w in ['news','announcement','أخبار','إعلانات'])
    wants_dividend  = any(w in msg_lower for w in ['dividend','distribution','توزيعات'])
    wants_financial = any(w in msg_lower for w in ['financial','profit','revenue','مالية','إيرادات'])
    wants_chart     = any(w in msg_lower for w in ['chart','رسم'])
    wants_ownership = any(w in msg_lower for w in ['ownership', 'non omani', 'nonomani', 'gcc', 'foreign', 'arab', 'shareholder', 'ملكية', 'غير عماني', 'أجانب'])
    wants_board     = any(w in msg_lower for w in ['board','director','مجلس','إدارة'])

    # Step 6: Fetch from MSX.om APIs
    from services.msx_api import (
        get_company_info as msx_company,
        get_snap_last4_years, get_snap_financial,
        get_snap_news, get_dividends, get_chart_data,
        get_company_news, get_snap_last20_trades, get_bod_members,
        get_snap_ownership_structure,
    )
    from services.msx_parser import format_snapshot_for_ai, flatten_any

    tasks = [msx_company(symbol), get_snap_last4_years(symbol)]
    if wants_news:      tasks += [get_snap_news(symbol), get_company_news(symbol)]
    if wants_dividend:  tasks += [get_dividends(symbol)]
    if wants_financial: tasks += [get_snap_financial(symbol)]
    if wants_chart:     tasks += [get_chart_data(symbol, _detect_chart_period(message))]
    if wants_board:     tasks += [get_bod_members(symbol)]
    if wants_ownership: tasks += [get_snap_ownership_structure(symbol)]
    if not any([wants_news, wants_dividend, wants_financial, wants_chart, wants_board, wants_ownership]):
        tasks += [get_snap_last20_trades(symbol)]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Parse snapshot with structured parser
    snapshot = results[0] if results and not isinstance(results[0], Exception) else None
    if snapshot:
        context.append("\n" + format_snapshot_for_ai(symbol, snapshot))
    else:
        context.append(f"\n⚠️ Live price unavailable. Visit: https://www.msx.om/snapshot.aspx?s={symbol}")

    # Last 4 years
    last4 = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else None
    if last4:
        context.append("\n📅 Performance (Last 4 Years):")
        context.extend(flatten_any(last4)[:15])

    # Additional results
    labels = {2:"📰 News", 3:"📢 Announcements", 4:"💵 Dividends",
              5:"💰 Financial", 6:"📊 Chart", 7:"👥 Board"}
    for i, result in enumerate(results[2:], start=2):
        if result and not isinstance(result, Exception):
            context.append(f"\n{labels.get(i, '📌 Data')}:")
            context.extend(flatten_any(result)[:20])

    # Historical prices from MSSQL
    duration  = _detect_duration(message)
    today     = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    prices    = await _run_sync(_get_prices, symbol, duration, from_date, today)
    if prices:
        context.append("\n" + _format_prices(prices))

    return "\n".join(context)
