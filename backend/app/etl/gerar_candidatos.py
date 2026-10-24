"""
Gera clientes candidatos e pendências de consolidação usando componentes conexos.

Regras aplicadas:
1. Pula o cliente sentinela ("Não Informado").
2. Normaliza os nomes e aplica similaridade (limiar 85).
3. Usa Union-Find para agrupar componentes conexos (A~B e B~C -> grupo A,B,C).
4. Elege o nome oficial do grupo por ordem alfabética do nome normalizado.
5. Idempotente: ignora RawNames que já possuem pendência aberta.
"""

import asyncio
import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constantes import SENTINELA_NOME
from backend.app.db.session import AsyncSessionLocal
from backend.app.model.models import Client, PendingConsolidation, RawName
from backend.app.enum import ConsolidationStatus
from backend.app.enum.consolidacao import MotivoPendenciaEnum

from backend.app.services.matching.normalizacao import normalizar_nome_razao_social, NomeInvalidoError
from backend.app.services.matching.similaridade import encontrar_correspondencias

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("gerar_candidatos")

LIMIAR_SIMILARIDADE = 85.0


class UnionFind:
    """Estrutura clássica para encontrar componentes conexos em um grafo."""
    def __init__(self, elementos):
        self.parent = {e: e for e in elementos}

    def find(self, i):
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j

    def get_grupos(self):
        grupos = defaultdict(list)
        for e in self.parent:
            grupos[self.find(e)].append(e)
        return list(grupos.values())


async def gerar_candidatos(session: AsyncSession):
    # 1. Buscar RawNames sem cliente atribuído (excluindo o Sentinela)
    stmt_raw = select(RawName).where(
        RawName.cliente_id.is_(None),
        RawName.nome_bruto != SENTINELA_NOME
    )
    raw_names = (await session.scalars(stmt_raw)).all()

    if not raw_names:
        logger.info("Nenhum nome bruto pendente de atribuição encontrado.")
        return

    # 2. Filtrar os que já possuem pendência gerada (Idempotência)
    stmt_existentes = select(PendingConsolidation.nome_bruto_id).where(
        PendingConsolidation.motivo_pendencia == MotivoPendenciaEnum.consolidacao_nome
    )
    ids_ja_pendentes = set((await session.scalars(stmt_existentes)).all())

    raw_names_elegiveis = [rn for rn in raw_names if rn.id not in ids_ja_pendentes]

    if not raw_names_elegiveis:
        logger.info("Todos os nomes brutos já possuem sugestões geradas. Nada a fazer.")
        return

    logger.info(f"Processando {len(raw_names_elegiveis)} nomes brutos elegíveis...")

    # 3. Normalização
    norm_to_raw = defaultdict(list)
    nomes_normalizados_unicos = set()

    for rn in raw_names_elegiveis:
        try:
            nome_norm = normalizar_nome_razao_social(rn.nome_bruto)
        except NomeInvalidoError:
            # Fallback seguro caso a normalização limpe o nome inteiro
            nome_norm = rn.nome_bruto.upper().strip()
        
        norm_to_raw[nome_norm].append(rn)
        nomes_normalizados_unicos.add(nome_norm)

    # 4. Cálculo de Similaridade em lote
    logger.info(f"Calculando similaridade para {len(nomes_normalizados_unicos)} nomes únicos...")
    correspondencias = encontrar_correspondencias(
        nomes_normalizados_unicos, 
        limiar=LIMIAR_SIMILARIDADE
    )
    logger.info(f"{len(correspondencias)} correspondências encontradas (>= {LIMIAR_SIMILARIDADE}%).")

    # 5. Agrupamento (Union-Find)
    uf = UnionFind(nomes_normalizados_unicos)
    for corr in correspondencias:
        uf.union(corr.nome_origem, corr.nome_candidato)

    grupos_normalizados = uf.get_grupos()
    logger.info(f"{len(grupos_normalizados)} grupos únicos (candidatos a Cliente) formados.")

    # 6. Criação de Clientes e Pendências no Banco
    clientes_criados = 0
    pendencias_criadas = 0

    for grupo_norm in grupos_normalizados:
        # A escolha do nome oficial é o primeiro alfabeticamente
        grupo_ordenado = sorted(grupo_norm)
        nome_oficial = grupo_ordenado[0]

        # Cria o cliente candidato
        novo_cliente = Client(nome_oficial=nome_oficial)
        session.add(novo_cliente)
        await session.flush()  # Garante a geração do novo_cliente.id (UUID)
        clientes_criados += 1

        # Para cada nome normalizado neste grupo...
        for nome_norm in grupo_norm:
            # ... pega todos os RawNames originais que geraram esse nome normalizado
            for rn in norm_to_raw[nome_norm]:
                pendencia = PendingConsolidation(
                    nome_bruto_id=rn.id,
                    cliente_sugerido_id=novo_cliente.id,
                    motivo_pendencia=MotivoPendenciaEnum.consolidacao_nome,
                    status=ConsolidationStatus.pendente,
                    # score_similaridade omitido intencionalmente (difícil cravar um 
                    # único número quando o grupo é formado por componentes conexos)
                    score_similaridade=None 
                )
                session.add(pendencia)
                pendencias_criadas += 1

    await session.commit()
    
    logger.info("====== RESUMO DA GERAÇÃO DE CANDIDATOS ======")
    logger.info(f" -> Nomes brutos processados : {len(raw_names_elegiveis)}")
    logger.info(f" -> Clientes gerados       : {clientes_criados}")
    logger.info(f" -> Pendências criadas     : {pendencias_criadas}")
    logger.info("=============================================")


if __name__ == "__main__":
    asyncio.run(gerar_candidatos(AsyncSessionLocal()))