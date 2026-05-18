"""
Seed script - populates PostgreSQL with all sample MSX data.
Run: python seed.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:root@localhost:5432/Chatboot"

SAMPLE_FAQS = [
    {"question": "What services does MSX offer?", "answer": "MSX offers a wide range of IT and technology services including software development, cloud solutions, infrastructure management, and digital transformation consulting.", "category": "general", "is_active": True},
    {"question": "How can I contact MSX support?", "answer": "You can reach MSX support through:\n- Website: www.msx.om\n- Email: support@msx.om\n- Phone: +968 XXXX XXXX\n- Working hours: Sunday-Thursday, 8am-5pm GST", "category": "support", "is_active": True},
    {"question": "What are your working hours?", "answer": "MSX operates Sunday through Thursday, 8:00 AM to 5:00 PM Gulf Standard Time (GST). For urgent issues outside business hours, please use our online support portal.", "category": "support", "is_active": True},
    {"question": "How do I request a quote?", "answer": "To request a quote, please visit www.msx.om/contact or email sales@msx.om with your project requirements. Our sales team will respond within 1-2 business days.", "category": "sales", "is_active": True},
    {"question": "Do you offer training services?", "answer": "Yes, MSX provides professional training in various technology domains. Contact us at training@msx.om for the current course catalog and scheduling.", "category": "general", "is_active": True},
]

SAMPLE_KB = [
    {"title": "MSX Company Overview", "content": "MSX is a leading technology solutions provider based in Oman. We specialize in delivering innovative IT services and digital transformation solutions to organizations across the Gulf region.", "category": "company", "tags": ["overview", "company", "services"], "source": "https://www.msx.om/about"},
    {"title": "Support Escalation Process", "content": "Level 1 Support: Initial contact via chat or email. Response time: 4 hours.\nLevel 2 Support: Technical specialists. Response time: 8 hours.\nLevel 3 Support: Senior engineers. Response time: 24 hours.\nCritical issues (P1): Immediate escalation, 1-hour response SLA.", "category": "support", "tags": ["support", "escalation", "sla"], "source": None},
    {"title": "Cloud Services Portfolio", "content": "MSX offers comprehensive cloud services including: AWS migration and management, Microsoft Azure solutions, private cloud deployment, hybrid cloud architecture, cloud cost optimization, and 24/7 cloud monitoring.", "category": "services", "tags": ["cloud", "aws", "azure"], "source": "https://www.msx.om/services/cloud"},
]

SAMPLE_ENDPOINTS = [
    {
        "name": "Company Snapshot",
        "description": "Main company info, live price, market data",
        "url": "https://www.msx.om/snapshot.aspx/company",
        "method": "POST",
        "body": {"Symbol": "{Symbol}"},
        "headers": {},
        "keywords_en": ["price", "stock", "company", "info", "snapshot", "about"],
        "keywords_ar": ["سعر", "شركة", "معلومات", "بيانات"],
        "category": "company", "is_active": True,
    },
    {
        "name": "Last 4 Years Performance",
        "description": "Annual performance summary for last 4 years",
        "url": "https://www.msx.om/snapshot.aspx/SnapLast4years",
        "method": "POST",
        "body": {"Symbol": "{Symbol}"},
        "headers": {},
        "keywords_en": ["performance", "annual", "yearly", "history", "years"],
        "keywords_ar": ["أداء", "سنوي", "تاريخ", "سنوات"],
        "category": "company", "is_active": True,
    },
    {
        "name": "Last 20 Trades",
        "description": "Last 20 trading transactions",
        "url": "https://www.msx.om/snapshot.aspx/SnapLast20trades",
        "method": "POST",
        "body": {"Symbol": "{Symbol}"},
        "headers": {},
        "keywords_en": ["trade", "trading", "transaction", "last trades", "recent"],
        "keywords_ar": ["صفقات", "تداول", "أخر صفقات"],
        "category": "trading", "is_active": True,
    },
    {
        "name": "Financial Statements",
        "description": "Financial results, profit, revenue",
        "url": "https://www.msx.om/snapshot.aspx/SnapFinancial",
        "method": "POST",
        "body": {"Symbol": "{Symbol}"},
        "headers": {},
        "keywords_en": ["financial", "profit", "revenue", "earnings", "income", "balance"],
        "keywords_ar": ["مالية", "أرباح", "إيرادات", "نتائج مالية", "ميزانية"],
        "category": "financial", "is_active": True,
    },
    {
        "name": "Company News",
        "description": "Latest company news and announcements",
        "url": "https://www.msx.om/snapshot.aspx/SnapNews",
        "method": "POST",
        "body": {"Symbol": "{Symbol}"},
        "headers": {},
        "keywords_en": ["news", "announcement", "update", "press release"],
        "keywords_ar": ["أخبار", "إعلانات", "بيانات صحفية", "إشعارات"],
        "category": "news", "is_active": True,
    },
    {
        "name": "Dividend Distribution",
        "description": "Dividend history and distribution reports",
        "url": "https://www.msx.om/snapshot.aspx/DividendDistributionReports",
        "method": "POST",
        "body": {"Symbol": "{Symbol}"},
        "headers": {},
        "keywords_en": ["dividend", "distribution", "cash", "payout", "yield"],
        "keywords_ar": ["توزيعات", "أرباح نقدية", "توزيع أرباح", "عائد"],
        "category": "financial", "is_active": True,
    },
    {
        "name": "Chart Data (1 Month)",
        "description": "Price chart data for last 1 month",
        "url": "https://www.msx.om/snapshot.aspx/CompanyChartData",
        "method": "POST",
        "body": {"Symbol": "{Symbol}", "Period": "1m"},
        "headers": {},
        "keywords_en": ["chart", "graph", "price history", "1 month"],
        "keywords_ar": ["رسم بياني", "تاريخ الأسعار", "شهر"],
        "category": "chart", "is_active": True,
    },
    {
        "name": "Board of Directors",
        "description": "BOD members and management",
        "url": "https://www.msx.om/BODMembersSnap.aspx?s={symbol}",
        "method": "GET",
        "body": None,
        "headers": {},
        "keywords_en": ["board", "director", "management", "BOD", "members"],
        "keywords_ar": ["مجلس الإدارة", "أعضاء", "مدراء", "إدارة"],
        "category": "governance", "is_active": True,
    },
    {
        "name": "Subsidiaries & Associates",
        "description": "Company subsidiaries and associated companies",
        "url": "https://www.msx.om/SubsidiariesandAssociatesSnap.aspx?s={symbol}",
        "method": "GET",
        "body": None,
        "headers": {},
        "keywords_en": ["subsidiary", "subsidiaries", "associate", "affiliate", "related company"],
        "keywords_ar": ["شركات تابعة", "شركات مرتبطة", "مشاركات"],
        "category": "company", "is_active": True,
    },
    {
        "name": "Company News (Annual)",
        "description": "Full year news and announcements",
        "url": "https://www.msx.om/company-news.aspx?s={symbol}&y=2026&f=1&t=5&i=",
        "method": "GET",
        "body": None,
        "headers": {},
        "keywords_en": ["annual news", "yearly announcements", "2026 news"],
        "keywords_ar": ["أخبار سنوية", "إعلانات السنة"],
        "category": "news", "is_active": True,
    },
    {
        "name": "Sustainability Reports",
        "description": "ESG and sustainability reports",
        "url": "https://www.msx.om/snapshot.aspx/SustainabilityReports",
        "method": "POST",
        "body": {"Symbol": "{Symbol}", "Year": "2025", "Type": "E"},
        "headers": {},
        "keywords_en": ["sustainability", "ESG", "environment", "green"],
        "keywords_ar": ["استدامة", "بيئة", "مسؤولية اجتماعية"],
        "category": "governance", "is_active": True,
    },
    {
        "name": "Ownership Structure",
        "description": "Non-Omani, GCC, Arab, Foreign ownership breakdown",
        "url": "https://www.msx.om/snapshot.aspx/SnapOwnership",
        "method": "POST",
        "body": {"Symbol": "{Symbol}"},
        "headers": {},
        "keywords_en": ["ownership", "non omani", "nonomani", "gcc", "foreign", "arab", "shareholder", "investor"],
        "keywords_ar": ["ملكية", "غير عماني", "أجانب", "خليجي", "مساهمين", "عربي"],
        "category": "ownership", "is_active": True,
    },
    {
        "name": "Major Shareholders",
        "description": "Major shareholders list",
        "url": "https://www.msx.om/snapshot.aspx/SnapMajorShareholders",
        "method": "POST",
        "body": {"Symbol": "{Symbol}"},
        "headers": {},
        "keywords_en": ["major shareholder", "top shareholder", "largest shareholder", "stake"],
        "keywords_ar": ["كبار المساهمين", "أكبر المساهمين", "حصة"],
        "category": "ownership", "is_active": True,
    },
    {
        "name": "Corporate Governance Report",
        "description": "Corporate governance report",
        "url": "https://www.msx.om/snapshot.aspx/CorporateGovernanceReport",
        "method": "POST",
        "body": {"Symbol": "{Symbol}", "Year": "2025", "Type": "CGR"},
        "headers": {},
        "keywords_en": ["governance", "corporate", "compliance", "CGR"],
        "keywords_ar": ["حوكمة", "إدارة الشركات", "امتثال"],
        "category": "governance", "is_active": True,
    },
]


async def seed():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from database import Base
    import models

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All tables created/verified")

    async with async_session() as session:

        # ── FAQs ──────────────────────────────────────────────────
        await session.execute(text("DELETE FROM faqs"))
        await session.commit()
        for data in SAMPLE_FAQS:
            session.add(models.FAQ(**data))
        await session.commit()
        print(f"✅ Inserted {len(SAMPLE_FAQS)} FAQs")

        # ── Knowledge Base ─────────────────────────────────────────
        await session.execute(text("DELETE FROM knowledge_base"))
        await session.commit()
        for data in SAMPLE_KB:
            session.add(models.KnowledgeBase(**data))
        await session.commit()
        print(f"✅ Inserted {len(SAMPLE_KB)} knowledge base articles")

        # ── API Endpoints ──────────────────────────────────────────
        await session.execute(text("DELETE FROM api_endpoints"))
        await session.commit()
        for data in SAMPLE_ENDPOINTS:
            session.add(models.ApiEndpoint(**data))
        await session.commit()
        print(f"✅ Inserted {len(SAMPLE_ENDPOINTS)} API endpoints")

    await engine.dispose()
    print("\n🎉 Seed complete!")
    print("   → Start backend: python -m uvicorn main:app --host 0.0.0.0 --port 8001")
    print("   → Open admin:    http://localhost:5173/admin")


if __name__ == "__main__":
    asyncio.run(seed())
