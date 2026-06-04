import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.scheduler.models import Base


def _make_url() -> str:
    # Ruta absoluta o relativa; aiosqlite usa sqlite+aiosqlite:///<path>
    return f"sqlite+aiosqlite:///{settings.sqlite_path}"


engine = create_async_engine(_make_url(), echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Crea el directorio padre y las tablas SQLite si no existen."""
    db_dir = os.path.dirname(settings.sqlite_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
