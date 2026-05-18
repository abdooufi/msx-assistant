from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from database import create_tables, close_db
from cache import get_redis, close_redis
from routes import chat, knowledge, faq, admin, unanswered, auth
from routes import company, endpoints

settings = get_settings()

 
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await get_redis()  # Connect to Redis (optional — won't crash if unavailable)
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
    allow_origins=["*"],
    allow_credentials=False,
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
    cache = await get_cache_stats()
    return {"status": "ok", "cache": cache.get("status", "unknown")}
