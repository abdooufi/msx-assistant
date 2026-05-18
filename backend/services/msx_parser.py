"""
MSX.om API response parser.
Field names based on real API response from /snapshot.aspx/company
"""
import json
from typing import Optional, Dict, Any, List


# Exact field mapping from real MSX API response
FIELD_MAP = {
    # Price
    'LTP':           'Last Price',
    'ClosePrice':    'Close Price',
    'OpenPrice':     'Open Price',
    'High':          'High',
    'Low':           'Low',
    'PrevClose':     'Previous Close',
    # Change
    'Change':        'Change %',
    'ChangeVal':     'Change Value',
    'Image':         'Trend',
    # Volume
    'Volume':        'Volume',
    'LTV':           'Last Trade Volume',
    'Turnover':      'Turnover',
    'NoOfTrades':    'No. of Trades',
    # Bid/Ask
    'BidPrice':      'Bid Price',
    'BidVolume':     'Bid Volume',
    'AskPrice':      'Ask Price',
    'AskVolume':     'Ask Volume',
    # Company
    'Symbol':        'Symbol',
    'ShortNameEn':   'Name (EN)',
    'ShortNameAr':   'Name (AR)',
    'LongNameEn':    'Full Name (EN)',
    'LongNameAr':    'Full Name (AR)',
    'GroupEn':       'Market Group',
    'GroupAr':       'Market Group (AR)',
    'MarketID':      'Market ID',
    'Type':          'Type',
    # Ownership fields
    'NonOmani':      'Non-Omani Ownership %',
    'GCC':           'GCC Ownership %',
    'Arab':          'Arab Ownership %',
    'Foreign':       'Foreign Ownership %',
    'Omani':         'Omani Ownership %',
    'NonOmaniPct':   'Non-Omani %',
    'GCCPct':        'GCC %',
    'ArabPct':       'Arab %',
    'ForeignPct':    'Foreign %',
    'OmaniPct':      'Omani %',
    # Status
    'QuarterStatusEn': 'Quarter Status',
}

PRIORITY_FIELDS = [
    'Last Price', 'Change %', 'Change Value', 'Trend',
    'Open Price', 'High', 'Low', 'Previous Close',
    'Volume', 'Turnover', 'No. of Trades',
    'Last Trade Volume', 'Bid Price', 'Ask Price',
    'Market Group',
    'Non-Omani Ownership %', 'GCC Ownership %',
    'Arab Ownership %', 'Foreign Ownership %', 'Omani Ownership %',
    'Non-Omani %', 'GCC %', 'Arab %', 'Foreign %', 'Omani %',
]


def _clean(v) -> Optional[str]:
    if v is None: return None
    s = str(v).strip()
    if not s or s in ('None', 'null', '', '-', 'N/A', '0', '0.00', '0.000'): return None
    if '${' in s or 'AnswerValue' in s: return None
    return s


def _unwrap(data: Any) -> Any:
    """Unwrap ASP.NET {"d": ...} response."""
    if isinstance(data, dict) and 'd' in data:
        inner = data['d']
        if isinstance(inner, str):
            try: return json.loads(inner)
            except: return inner
        return inner
    return data


def parse_company_snapshot(data: Any) -> Dict[str, str]:
    """Parse MSX snapshot response into clean key-value dict."""
    data = _unwrap(data)

    if isinstance(data, str):
        try: data = json.loads(data)
        except: return {}

    if isinstance(data, list):
        if not data: return {}
        data = data[0]

    if not isinstance(data, dict):
        return {}

    result = {}
    for api_key, label in FIELD_MAP.items():
        val = data.get(api_key)
        cleaned = _clean(val)
        if cleaned and label not in result:
            result[label] = cleaned

    # Also capture any unknown fields that look like ownership %
    for k, v in data.items():
        if k not in FIELD_MAP:
            cleaned = _clean(v)
            if cleaned and any(w in k.lower() for w in ['omani', 'gcc', 'arab', 'foreign', 'owner', 'share']):
                result[f'{k}'] = cleaned

    return result


def format_snapshot_for_ai(symbol: str, data: Any) -> str:
    """Format company snapshot as clean text for AI."""
    parsed = parse_company_snapshot(data)

    lines = [f"📊 Live Market Data for {symbol.upper()} (MSX.om - Real Time):"]

    if parsed:
        shown = set()
        for field in PRIORITY_FIELDS:
            if field in parsed:
                lines.append(f"  • {field}: {parsed[field]}")
                shown.add(field)
        for k, v in parsed.items():
            if k not in shown:
                lines.append(f"  • {k}: {v}")
    else:
        lines.append(f"  ⚠️ No live data. Visit: https://www.msx.om/snapshot.aspx?s={symbol}")

    return "\n".join(lines)


def flatten_any(data: Any, prefix: str = "", depth: int = 0) -> List[str]:
    """Recursively flatten any API response into readable lines."""
    lines = []
    if depth > 4 or data is None:
        return lines

    data = _unwrap(data)

    if isinstance(data, dict):
        for k, v in list(data.items())[:40]:
            key = f"{prefix}.{k}" if prefix else k
            sub = flatten_any(v, key, depth + 1)
            if sub:
                lines.extend(sub)
            else:
                val = _clean(v)
                if val:
                    lines.append(f"  • {key}: {val}")

    elif isinstance(data, list):
        for i, item in enumerate(data[:10]):
            lines.extend(flatten_any(item, f"{prefix}[{i+1}]" if prefix else f"[{i+1}]", depth + 1))

    else:
        val = _clean(data)
        if val:
            lines.append(f"  • {prefix}: {val}" if prefix else f"  {val}")

    return lines
