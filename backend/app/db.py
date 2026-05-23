from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.config import get_settings


engine: AsyncEngine = create_async_engine(
    get_settings().database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)


async def get_conn() -> AsyncIterator[AsyncConnection]:
    async with engine.begin() as conn:
        yield conn
