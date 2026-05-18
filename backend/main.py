from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from config import get_settings
from database import create_tables, close_db
from cache import get_redis, close_redis
from routes import chat, knowledge, faq, admin, unanswered, auth
from routes import company, endpoints

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await get_redis()  # Redis is optional — won't crash if unavailable

    # MSSQL startup check (informational only — app runs without it)
    try:
        from mssql import test_mssql_connection
        ok, msg = await asyncio.get_event_loop().run_in_executor(None, test_mssql_connection)
        if ok:
            print(f"✅ MSSQL connected ({settings.mssql_server})")
        else:
            print(f"⚠️  MSSQL unavailable — company queries will be limited: {msg}")
    except Exception as e:
        print(f"⚠️  MSSQL check error: {e}")

    print(f"🚀 {settings.app_name} v{settings.app_version} started")
    yield
    await close_redis()
    await close_db()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered assistant for MSX.om",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(faq.router)
app.include_router(admin.router)
app.include_router(unanswered.router)
app.include_router(company.router)
app.include_router(endpoints.router)


@app.get("/")
async def root():
    return {"app": settings.app_name, "version": settings.app_version, "docs": "/docs", "status": "running"}

@app.get("/health")
async def health():
    from cache import get_cache_stats
    from mssql import test_mssql_connection
    cache = await get_cache_stats()
    mssql_ok, mssql_msg = await asyncio.get_event_loop().run_in_executor(None, test_mssql_connection)
    return {
        "status": "ok",
        "cache": cache.get("status", "unknown"),
        "mssql": "connected" if mssql_ok else f"unavailable: {mssql_msg}",
    }
