"""
Fixtures compartilhadas para os testes do model, pipeline de matching e da API.
"""

import asyncio
import sys
import uuid

# asyncpg não é totalmente compatível com o ProactorEventLoop, o loop
# padrão no Windows — a conexão pode ser fechada "no meio da operação"
# de forma intermitente. WindowsSelectorEventLoopPolicy resolve.
# Precisa ser definido ANTES de qualquer loop/fixture assíncrona rodar.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from backend.app.core.security import hash_password
from backend.app.db.session import get_db
from backend.app.model.models import (
    Base,
    Client,
    GenerationProject,
    PendingConsolidation,
    RawName,
    User,
)
from backend.main import app


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
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
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


@pytest_asyncio.fixture()
async def client(db_session):
    """
    AsyncClient contra a app real, com get_db sobrescrito para usar a
    mesma db_session da transação do teste — assim o que o endpoint
    grava (ex.: refresh_token) é visível pro teste, e some no rollback.
    """
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def usuario_ativo(db_session):
    usuario = User(
        email="teste@painel.com",
        senha_hash=hash_password("senha-correta-123"),
        papel="admin",
        ativo=True,
    )
    db_session.add(usuario)
    await db_session.commit()
    await db_session.refresh(usuario)
    return usuario


@pytest_asyncio.fixture()
async def usuario_inativo(db_session):
    usuario = User(
        email="desligado@painel.com",
        senha_hash=hash_password("senha-correta-123"),
        papel="admin",
        ativo=False,
    )
    db_session.add(usuario)
    await db_session.commit()
    await db_session.refresh(usuario)
    return usuario


# =====================================================================
# FIXTURES DO PIPELINE DE MATCHING E REGRESSÃO (SPEs)
# =====================================================================


@pytest_asyncio.fixture()
async def seeded_clients(db_session: AsyncSession) -> dict[str, Client]:
    """
    Popula o banco com o Cliente oficial alvo ('Ventos de São Carlos Oficial')
    e clientes distratores com nomes semelhantes para validar que o algoritmo
    de matching não gera falsos positivos.
    """
    target_client = Client(
        id=uuid.uuid4(),
        nome_oficial="Ventos de São Carlos Oficial",
    )
    distractor_1 = Client(
        id=uuid.uuid4(),
        nome_oficial="Ventos de São José Energia S.A.",
    )
    distractor_2 = Client(
        id=uuid.uuid4(),
        nome_oficial="São Carlos Solar Participações Ltda",
    )
    distractor_3 = Client(
        id=uuid.uuid4(),
        nome_oficial="Ventos do Nordeste Geradora",
    )

    db_session.add_all([target_client, distractor_1, distractor_2, distractor_3])
    await db_session.commit()

    for c in (target_client, distractor_1, distractor_2, distractor_3):
        await db_session.refresh(c)

    return {
        "target": target_client,
        "distractor_1": distractor_1,
        "distractor_2": distractor_2,
        "distractor_3": distractor_3,
    }


@pytest_asyncio.fixture()
async def ventos_sao_carlos_spes(
    db_session: AsyncSession,
) -> list[tuple[RawName, GenerationProject]]:
    """
    Cria o dataset de mock contendo as 12 SPEs (VENTOS DE SAO CARLOS 01 a 12)
    com variações reais de grafia (falta de acento, sufixos societários,
    espaços extras) e seus respectivos GenerationProjects vinculados.
    """
    spe_variations = [
        "VENTOS DE SAO CARLOS 01",
        "VENTOS DE SAO CARLOS 02 S.A.",
        "VENTOS DE SÃO CARLOS 03 ENERGIA EOLICA LTDA",
        "SPE VENTOS DE SAO CARLOS 04 S/A",
        "VENTOS DE SAO CARLOS 05 - GERADORA",
        "VENTOS DE SÃO CARLOS 06",
        "VENTOS DE SAO CARLOS 07 SPE LTDA.",
        "CENTRAL EOLICA VENTOS DE SAO CARLOS 08",
        "VENTOS DE SAO CARLOS 09 S.A",
        "VENTOS DE SÃO CARLOS 10 EMPREENDIMENTOS",
        "VENTOS DE SAO CARLOS 11",
        "  VENTOS DE SAO CARLOS 12  ",
    ]

    dataset: list[tuple[RawName, GenerationProject]] = []

    for index, raw_text in enumerate(spe_variations, start=1):
        raw_name = RawName(
            nome_bruto=raw_text,
            cliente_id=None,  # Começa sem vínculo para o pipeline processar
        )
        db_session.add(raw_name)
        await db_session.flush()  # Garante o raw_name.id (autoincrement) antes do commit

        project = GenerationProject(
            ceg=f"EOL.CV.PI.0300{index:02d}-0.01",
            uf="PI",
            municipios="Caldeirão Grande do Piauí, Marcolândia",
            potencia_outorgada_kw=30000.0,
            latitude=-7.3250 - (index * 0.001),
            longitude=-40.6380 - (index * 0.001),
            cliente_id=None,
            nome_bruto_principal_id=raw_name.id,
        )
        db_session.add(project)
        dataset.append((raw_name, project))

    await db_session.commit()

    for raw_name, project in dataset:
        await db_session.refresh(raw_name)
        await db_session.refresh(project)

    return dataset