from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings


settings = get_settings()
is_supabase_pooler = "pooler.supabase.com" in settings.database_url

engine_options = {"pool_pre_ping": True}
if is_supabase_pooler:
    engine_options["poolclass"] = NullPool
    engine_options["connect_args"] = {"prepared_statement_cache_size": 0}
else:
    engine_options["pool_size"] = 10
    engine_options["max_overflow"] = 20

engine: AsyncEngine = create_async_engine(settings.database_url, **engine_options)


async def get_conn() -> AsyncIterator[AsyncConnection]:
    async with engine.begin() as conn:
        yield conn
