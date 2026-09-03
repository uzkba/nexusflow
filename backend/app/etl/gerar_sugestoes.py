import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.model.models import RawName, Client
from backend.app.etl.matching import calcular_similaridade
from backend.app.services.consolidacao import salvar_sugestoes_em_massa

logger = logging.getLogger(__name__)

async def executar_geracao_de_sugestoes(session: AsyncSession, threshold: float = 85.0):
    """
    Busca os nomes brutos órfãos e a base de clientes, roda o RapidFuzz
    e grava as sugestões pendentes no banco.
    """
    logger.info("Iniciando pipeline de geração de sugestões...")

    # 1. Buscar nomes brutos que ainda não têm cliente associado
    stmt_brutos = select(RawName).where(RawName.cliente_id.is_(None))
    result_brutos = await session.execute(stmt_brutos)
    nomes_brutos = result_brutos.scalars().all()

    if not nomes_brutos:
        logger.info("Nenhum nome bruto pendente de consolidação.")
        return 0

    # 2. Buscar a base de clientes oficiais (para o dicionário do RapidFuzz)
    stmt_clientes = select(Client)
    result_clientes = await session.execute(stmt_clientes)
    clientes_base = result_clientes.scalars().all()

    if not clientes_base:
        logger.warning("Base de clientes vazia. Cancelando matching.")
        return 0

    # 3. Rodar o algoritmo de similaridade
    sugestoes = calcular_similaridade(nomes_brutos, clientes_base, threshold)

    if not sugestoes:
        logger.info("Nenhuma sugestão atingiu o score mínimo.")
        return 0

    # 4. Gravar no banco ignorando duplicatas (nossa task principal)
    linhas_inseridas = await salvar_sugestoes_em_massa(session, sugestoes)
    
    logger.info(f"Pipeline finalizado. {linhas_inseridas} sugestões salvas.")
    return linhas_inseridas