"""
Fixtures compartilhadas para os testes do model.

Async de ponta a ponta, com asyncpg — o mesmo driver usado em produção
(ver requirements.txt). Postgres real via testcontainers, não SQLite:
o model usa JSONB, UUID nativo e Enum nativo do Postgres, e SQLite não
implementa nenhum desses de verdade.

Requer Docker disponível na máquina que roda `pytest` (local ou CI).
Instalar: pip install -r requirements.txt (asyncpg já está lá) +
pip install pytest pytest-asyncio testcontainers[postgres] "psycopg[binary]"
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from backend.app.model.models import Base


@pytest.fixture(scope="session")
def postgres_container():
    """Sobe um Postgres real uma única vez para toda a sessão de testes."""
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container):
    # testcontainers devolve a URL com o driver síncrono (psycopg2) por
    # padrão — troca pro asyncpg, que é o driver real de produção.
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace("postgresql+psycopg2", "postgresql+asyncpg")

    eng = create_async_engine(async_url)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture()
async def db_session(engine):
    """
    Uma sessão por teste, isolada por transação com rollback ao final —
    cada teste começa com o banco limpo, sem precisar recriar o schema
    a cada execução (que seria lento).
    """
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    # se o teste provocou um erro de propósito (IntegrityError, enum
    # inválido), o driver já aborta a transação sozinho — chamar
    # rollback() de novo em cima disso é inofensivo, mas gera o
    # SAWarning "transaction already deassociated from connection".
    # is_active evita o aviso nesses casos sem mudar o comportamento.
    if transaction.is_active:
        await transaction.rollback()
    await connection.close()