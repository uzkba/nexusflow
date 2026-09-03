import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.app.model import PendingConsolidation

logger = logging.getLogger(__name__)

async def salvar_sugestoes_em_massa(session: AsyncSession, sugestoes: list[dict]) -> int:
    """
    Recebe uma lista de dicionários e insere na tabela consolidacoes_pendentes.
    """
    if not sugestoes:
        logger.info("Nenhuma sugestão de consolidação para salvar.")
        return 0

    stmt = pg_insert(PendingConsolidation).values(sugestoes)
    stmt = stmt.on_conflict_do_nothing(
        constraint='uix_nome_bruto_cliente_sugerido'
    )

    try:
        result = await session.execute(stmt)
        await session.commit()

        linhas_inseridas = result.rowcount
        logger.info(f"Foram gravadas {linhas_inseridas} novas sugestões de consolidação.")

        return linhas_inseridas
    except Exception as e:
        await session.rollback()
        logger.error(f"Erro ao salvar sugestões de consolidação: {str(e)}")
        raise e