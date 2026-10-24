"""
Script de Seed (Exclusivo para Desenvolvimento).
Aprova todas as pendências de consolidação existentes usando a camada de serviço.
Isso destrava os projetos para aparecerem no Dashboard (cliente_id IS NOT NULL).
"""

import asyncio
import logging
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import AsyncSessionLocal
from backend.app.services.consolidacoes_service import listar_pendentes, aprovar_pendencia
from backend.app.services.dashboard_service import get_kpis

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("seed_dev")


async def aprovar_tudo_e_mostrar_kpis():
    # 1. Proteção de Segurança: Recusa rodar fora de dev
    db_url = os.getenv("DATABASE_URL", "")
    if "localhost" not in db_url and "127.0.0.1" not in db_url:
        logger.error("ERRO FATAL: Tentativa de rodar o Seed fora do ambiente local.")
        logger.error(f"DATABASE_URL atual: {db_url}")
        raise SystemExit(1)

    usuario_fake_id = None # Mock de usuário para o registro de auditoria

    async with AsyncSessionLocal() as db:
        # 2. Listar todas as pendências
        pendentes = await listar_pendentes(db)
        total = len(pendentes)
        
        if total == 0:
            logger.info("Nenhuma pendência encontrada. Banco já está consolidado?")
        else:
            logger.info(f"Iniciando aprovação em massa de {total} grupos...")
            
            # 3. Aprovar uma a uma usando a regra de negócio real
            for i, p in enumerate(pendentes, 1):
                await aprovar_pendencia(db, p["id"], usuario_fake_id)
                if i % 100 == 0:
                    logger.info(f" -> {i}/{total} aprovadas...")
            
            logger.info("Todas as pendências foram aprovadas com sucesso!")

        # 4. Prova de Fogo: Mostrar os KPIs atualizados
        logger.info("Calculando KPIs do Dashboard (Card 30)...")
        kpis = await get_kpis(db)
        
        logger.info("====== KPIs ATUAIS DO DASHBOARD ======")
        logger.info(f"Total Projetos         : {kpis.get('total_projetos')}")
        logger.info(f"Total Clientes         : {kpis.get('total_clientes')}")
        logger.info(f"Potência Total (MW)    : {kpis.get('potencia_total_mw'):.2f}")
        logger.info(f"Projetos Pendentes     : {kpis.get('projetos_pendentes_revisao')}")
        logger.info("======================================")

        if kpis.get("total_projetos", 0) == 0:
            logger.error("FALHA: Os projetos continuam zerados no dashboard. O cliente_id não foi propagado.")
        else:
            logger.info("SUCESSO: Dados destravados para os gráficos!")


if __name__ == "__main__":
    asyncio.run(aprovar_tudo_e_mostrar_kpis())