"""Database and Redis session management."""

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mnemosyne.config import settings


def _async_url(url: str) -> str:
    """Ensure the database URL uses the asyncpg driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# PostgreSQL (async)
engine = create_async_engine(_async_url(settings.database_url), echo=False, pool_size=20, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Redis
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_redis() -> redis.Redis:
    return redis_client
