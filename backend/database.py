from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        from models import KnowledgeBase, FAQ, Conversation, UnansweredQuestion
        await conn.run_sync(Base.metadata.create_all)
    print("✅ PostgreSQL tables created")


async def close_db():
    await engine.dispose()
    print("🔌 PostgreSQL connection closed")
