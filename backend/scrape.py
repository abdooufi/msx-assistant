"""
MSX.om Unified Scraper
Merged from: msx_rag_project/scrape.py + original scrape.py

Steps:
1. Get all URLs from sitemap.aspx
2. Scrape each URL for content
3. Get company codes from MSSQL → scrape snapshot pages
4. Save to PostgreSQL knowledge_base table
5. Save msx_data.json for ChromaDB/RAG loading
"""
import asyncio
import httpx
import re
import time
import json
import os
from datetime import datetime
from typing import Optional, List, Dict
from urllib.parse import urljoin, urlparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:root@localhost:5432/Chatboot"
BASE_URL     = "https://www.msx.om"
SITEMAP_URL  = "https://www.msx.om/sitemap.aspx"
DELAY        = 0.5
MAX_CONTENT  = 5000
TIMEOUT      = 20
OUTPUT_JSON  = "msx_data.json"    # for ChromaDB loading

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

SKIP_PATTERNS = [
    r'snapshot\.aspx\?s=',  # handled separately via MSSQL
    r'company-news',
    r'company-chart',
    r'BODMembers',
    r'Subsidiaries',
    r'login', r'logout', r'register',
    r'\.pdf$', r'\.xlsx$', r'\.doc$',
    r'javascript:', r'^#',
    r'facebook\.com', r'twitter\.com', r'linkedin\.com',
]

STATIC_PAGES = [
    "https://www.msx.om/default.aspx",
    "https://www.msx.om/companies.aspx",
    "https://www.msx.om/brokers.aspx",
    "https://www.msx.om/bonds.aspx",
    "https://www.msx.om/Listing.aspx",
    "https://www.msx.om/mutual-funds.aspx",
    "https://www.msx.om/Custodians.aspx",
    "https://www.msx.om/performance.aspx",
    "https://www.msx.om/sitemap.aspx",
]


# ─── HTML cleaner ─────────────────────────────────────────────────

def clean_html(html: str) -> str:
    for tag in ['script','style','nav','header','footer','noscript','iframe','svg']:
        html = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', ' ', html, flags=re.DOTALL|re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', ' ', html, flags=re.DOTALL)
    html = re.sub(r'<(?:br|p|div|h[1-6]|tr|li)[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = html.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')\
               .replace('&nbsp;',' ').replace('&quot;','"').replace('&#39;',"'")
    lines = [l.strip() for l in html.splitlines() if l.strip() and len(l.strip()) > 2]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def extract_title(html: str) -> str:
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE|re.DOTALL)
    if m:
        return re.sub(r'<[^>]+>', '', m.group(1)).strip()[:200]
    return "MSX Page"


def categorize_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if any(w in path for w in ['news','press','announcement']):      return 'news'
    if any(w in path for w in ['market','trade','index','stock']):   return 'market'
    if any(w in path for w in ['about','corporate','profile']):      return 'about'
    if any(w in path for w in ['service','product','solution']):     return 'services'
    if any(w in path for w in ['contact','support','help']):         return 'support'
    if any(w in path for w in ['rule','regulation','law','policy']): return 'regulations'
    if any(w in path for w in ['report','disclosure','financial']):  return 'reports'
    if any(w in path for w in ['member','broker','dealer']):         return 'members'
    if any(w in path for w in ['invest','ipo','listing']):           return 'investment'
    if any(w in path for w in ['education','learn','guide']):        return 'education'
    if any(w in path for w in ['snapshot','company']):               return 'company'
    return 'general'


def should_skip(url: str) -> bool:
    for p in SKIP_PATTERNS:
        if re.search(p, url, re.IGNORECASE):
            return True
    return False


# ─── Sitemap ──────────────────────────────────────────────────────

async def get_sitemap_urls(client: httpx.AsyncClient) -> List[str]:
    print(f"🗺️  Fetching sitemap: {SITEMAP_URL}")
    urls  = set()
    try:
        r    = await client.get(SITEMAP_URL, headers=HEADERS)
        html = r.text
        for href, _ in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE|re.DOTALL):
            href = href.strip()
            if href.startswith('/'): full = BASE_URL + href
            elif href.startswith('http'): full = href
            else: continue
            if 'msx.om' not in full: continue
            clean = full.split('#')[0].rstrip('/')
            if not should_skip(clean):
                urls.add(clean)
    except Exception as e:
        print(f"  ⚠️ Sitemap error: {e}")

    # Add static pages
    for p in STATIC_PAGES:
        if not should_skip(p):
            urls.add(p.rstrip('/'))

    print(f"✅ Found {len(urls)} URLs")
    return sorted(urls)


# ─── Page scraper ─────────────────────────────────────────────────

async def scrape_page(client: httpx.AsyncClient, url: str, coid: str = None) -> Optional[Dict]:
    try:
        r = await client.get(url, headers=HEADERS)
        if r.status_code != 200: return None
        if 'html' not in r.headers.get('content-type', ''): return None
        html     = r.text
        title    = extract_title(html)
        content  = clean_html(html)
        if len(content) < 100: return None
        if len(content) > MAX_CONTENT:
            content = content[:MAX_CONTENT] + '\n\n[Truncated]'
        return {
            "url":      url,
            "coid":     coid,
            "title":    title,
            "content":  content,
            "category": categorize_url(url),
        }
    except Exception as e:
        print(f"  ⚠️ Error: {url} → {e}")
        return None


# ─── MSSQL: get company codes ─────────────────────────────────────

def get_company_codes_from_mssql() -> List[str]:
    """Get all company symbols from MSSQL securities table."""
    try:
        import pyodbc
        from config import get_settings
        s = get_settings()
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={s.mssql_server},{s.mssql_port};"
            f"DATABASE={s.mssql_database};"
            f"UID={s.mssql_username};PWD={s.mssql_password};"
            f"TrustServerCertificate=yes;Encrypt=yes;",
            timeout=10
        )
        cursor = conn.cursor()
        # Try MSM_GEO_Live securities table first
        try:
            cursor.execute("SELECT [Symbol] FROM [MSM_GEO_Live].[dbo].[securities] WHERE [is_visible]=1 ORDER BY [Symbol]")
        except Exception:
            # Fallback to MSXdata.coamy (from rag project)
            cursor.execute("SELECT Symbol FROM securities")
        codes = [str(r[0]).strip() for r in cursor.fetchall() if r[0]]
        conn.close()
        print(f"✅ Got {len(codes)} company codes from MSSQL")
        return codes
    except Exception as e:
        print(f"⚠️ MSSQL error: {e} — skipping company snapshots")
        return []


# ─── Save to PostgreSQL ───────────────────────────────────────────

async def save_to_db(session: AsyncSession, page: Dict, models) -> bool:
    try:
        result = await session.execute(
            text("SELECT id FROM knowledge_base WHERE source = :url LIMIT 1"),
            {"url": page['url']}
        )
        existing = result.fetchone()
        now = datetime.utcnow()
        if existing:
            await session.execute(text("""
                UPDATE knowledge_base
                SET title=:title, content=:content, category=:category, updated_at=:now
                WHERE source=:url
            """), {'title': page['title'], 'content': page['content'],
                   'category': page['category'], 'url': page['url'], 'now': now})
            return False
        else:
            kb = models.KnowledgeBase(
                title=page['title'], content=page['content'],
                category=page['category'],
                tags=['msx.om', 'scraped', page['category']],
                source=page['url'], created_at=now, updated_at=now,
            )
            session.add(kb)
            return True
    except Exception as e:
        print(f"  ❌ DB error: {e}")
        return False


# ─── Main ─────────────────────────────────────────────────────────

async def scrape():
    print("=" * 60)
    print("  MSX.om Unified Scraper")
    print("  Saves to: PostgreSQL + msx_data.json (for ChromaDB)")
    print("=" * 60)

    engine        = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from database import Base
    import models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ PostgreSQL ready")

    all_docs   = []
    seen_urls  = set()
    inserted   = 0
    updated    = 0
    skipped    = 0

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, verify=False) as client:

        # 1. Sitemap URLs
        sitemap_urls = await get_sitemap_urls(client)
        print(f"\n🌐 Scraping {len(sitemap_urls)} sitemap pages...")

        async with async_session() as session:
            for i, url in enumerate(sitemap_urls, 1):
                if url in seen_urls: continue
                seen_urls.add(url)
                print(f"  [{i:3d}/{len(sitemap_urls)}] {url[:70]}")
                page = await scrape_page(client, url)
                if page:
                    all_docs.append(page)
                    is_new = await save_to_db(session, page, models)
                    inserted += is_new
                    updated  += not is_new
                    if (inserted + updated) % 10 == 0:
                        await session.commit()
                else:
                    skipped += 1
                await asyncio.sleep(DELAY)
            await session.commit()

        # 2. Company snapshot pages from MSSQL
        codes = get_company_codes_from_mssql()
        if codes:
            print(f"\n📸 Scraping {len(codes)} company snapshot pages...")
            async with async_session() as session:
                for i, coid in enumerate(codes, 1):
                    url = f"{BASE_URL}/snapshot.aspx?s={coid}"
                    if url in seen_urls: continue
                    seen_urls.add(url)
                    print(f"  [{i:3d}/{len(codes)}] snapshot:{coid}")
                    page = await scrape_page(client, url, coid=coid)
                    if page:
                        all_docs.append(page)
                        is_new = await save_to_db(session, page, models)
                        inserted += is_new
                        updated  += not is_new
                        if (inserted + updated) % 10 == 0:
                            await session.commit()
                    await asyncio.sleep(DELAY)
                await session.commit()

    # 3. Save msx_data.json for ChromaDB
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_docs, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved {len(all_docs)} pages to {OUTPUT_JSON}")

    await engine.dispose()

    print("\n" + "=" * 60)
    print(f"  ✅ Done!")
    print(f"  📄 Inserted : {inserted} new pages → PostgreSQL")
    print(f"  🔄 Updated  : {updated} pages → PostgreSQL")
    print(f"  ⏭️  Skipped  : {skipped} pages")
    print(f"  📦 JSON     : {len(all_docs)} pages → {OUTPUT_JSON}")
    print("=" * 60)
    print("\n📌 Next step: Run load_chroma.py to build ChromaDB vector index")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Test single URL
        async def test():
            async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as c:
                page = await scrape_page(c, sys.argv[1])
                if page:
                    print(f"Title: {page['title']}")
                    print(f"Category: {page['category']}")
                    print(f"Content ({len(page['content'])} chars):")
                    print(page['content'][:500])
                else:
                    print("❌ No content")
        asyncio.run(test())
    else:
        asyncio.run(scrape())
