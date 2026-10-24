"""
Camada de serviço do fluxo de aprovação unificado (/api/consolidacoes),
sobre PendingConsolidation em backend/app/model/models.py.

A rota permanece "burra": só chama estas funções e devolve o resultado.
Toda regra de negócio - inclusive a limpeza condicional de diff_pendente -
fica aqui.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status as http_status
from sqlalchemy import or_, select, update, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.model.models import PendingConsolidation, RawName, GenerationProject, Client
from backend.app.enum import ConsolidationStatus
from backend.app.enum.projeto_geracao import ReviewStatus
from backend.app.enum.consolidacao import MotivoPendenciaEnum


async def listar_pendentes(db: AsyncSession) -> list[dict]:
    """
    Retorna todas as pendências enriquecidas com agregados (UFs, municípios, 
    total de projetos, potência total) e os nomes de domínio.
    """
    stmt = (
        select(
            PendingConsolidation,
            RawName.nome_bruto,
            Client.nome_oficial.label("cliente_sugerido_nome"),
            GenerationProject
        )
        .options(selectinload(PendingConsolidation.cegs_relacionados))
        .outerjoin(RawName, PendingConsolidation.nome_bruto_id == RawName.id)
        .outerjoin(Client, PendingConsolidation.cliente_sugerido_id == Client.id)
        # Traz projetos vinculados tanto por nome (consolidacao) quanto por CEG (alteracao)
        .outerjoin(
            GenerationProject,
            or_(
                GenerationProject.nome_bruto_principal_id == PendingConsolidation.nome_bruto_id,
                GenerationProject.ceg == PendingConsolidation.ceg
            )
        )
        .where(PendingConsolidation.status == ConsolidationStatus.pendente)
    )

    resultado = await db.execute(stmt)
    linhas = resultado.all()

    # Dicionário temporário para agrupar por ID da pendência
    pendentes_dict = {}

    for linha in linhas:
        (pendencia, nome_bruto, cliente_sugerido_nome, projeto) = linha
        pid = pendencia.id

        # Inicializa se for a primeira vez que a pendência aparece no join
        if pid not in pendentes_dict:
            pendentes_dict[pid] = {
                "id": pendencia.id,
                "motivo_pendencia": pendencia.motivo_pendencia,
                "status": pendencia.status,
                "nome_bruto_id": pendencia.nome_bruto_id,
                "nome_bruto": nome_bruto,
                "cliente_sugerido_id": pendencia.cliente_sugerido_id,
                "cliente_sugerido_nome": cliente_sugerido_nome,
                "score_similaridade": pendencia.score_similaridade,
                "ceg": pendencia.ceg,
                "diff_pendente": pendencia.diff_pendente,
                "decidido_por": pendencia.decidido_por,
                "decidido_em": pendencia.decidido_em,
                "cegs_relacionados": pendencia.cegs_relacionados,
                
                # Campos internos para agregação iterativa segura (set)
                "_ufs": set(),
                "_municipios": set(),
                "_projetos_vistos": set(),
                "potencia_total_kw": 0.0,
            }

        # Acumula os dados dos projetos vinculados
        if projeto and projeto.ceg not in pendentes_dict[pid]["_projetos_vistos"]:
            curr = pendentes_dict[pid]
            curr["_projetos_vistos"].add(projeto.ceg)
            curr["potencia_total_kw"] += (projeto.potencia_outorgada_kw or 0.0)
            
            if projeto.uf:
                curr["_ufs"].add(projeto.uf)
            if projeto.municipios:
                # municipios no modelo é list[str]
                curr["_municipios"].update(projeto.municipios)

    # Conta quantos nomes foram sugeridos para o mesmo cliente_sugerido_id em todo o pool
    contagem_sugeridos = Counter(
        p["cliente_sugerido_id"] for p in pendentes_dict.values() if p["cliente_sugerido_id"]
    )

    resultados_finais = []
    
    # Formatação final
    for p in pendentes_dict.values():
        p["ufs"] = sorted(list(p["_ufs"]))
        p["municipios"] = sorted(list(p["_municipios"]))
        p["total_projetos"] = len(p["_projetos_vistos"])
        p["potencia_total_mw"] = p["potencia_total_kw"] / 1000.0  # Conversão exigida pelo negócio
        p["nomes_sugeridos_para_cliente"] = contagem_sugeridos.get(p["cliente_sugerido_id"], 0)

        # Limpa o lixo temporário do dicionário
        del p["_ufs"], p["_municipios"], p["_projetos_vistos"], p["potencia_total_kw"]
        resultados_finais.append(p)

    # Ordena alfabeticamente pelo nome sugerido para organizar os grupos na tela
    return sorted(
        resultados_finais, 
        key=lambda x: (x["cliente_sugerido_nome"] or "", x["nome_bruto"] or "")
    )


async def _buscar_pendencia(db: AsyncSession, item_id: int) -> PendingConsolidation:
    resultado = await db.execute(
        select(PendingConsolidation)
        .options(selectinload(PendingConsolidation.cegs_relacionados))
        .where(PendingConsolidation.id == item_id)
    )
    item = resultado.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Pendência não encontrada"
        )
    if item.status != ConsolidationStatus.pendente:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Pendência já foi decidida",
        )
    return item


async def aprovar_pendencia(
    db: AsyncSession, item_id: int, usuario_id: UUID
) -> PendingConsolidation:
    """
    Aprova a pendência. Aplica as mudanças no banco dependendo do motivo.
    """
    item = await _buscar_pendencia(db, item_id)

    item.status = ConsolidationStatus.aprovado
    item.decidido_por = usuario_id
    item.decidido_em = datetime.now(timezone.utc)

    if item.motivo_pendencia == MotivoPendenciaEnum.consolidacao_nome:
        raw_name = await db.get(RawName, item.nome_bruto_id)
        if not raw_name:
            raise HTTPException(status_code=404, detail="Nome bruto não encontrado")

        # 1. Atualizar o RawName com o cliente oficial sugerido
        raw_name.cliente_id = item.cliente_sugerido_id

        # 2. Propagar o cliente_id para os projetos
        stmt_projetos = update(GenerationProject).where(
            GenerationProject.nome_bruto_principal_id == item.nome_bruto_id
        ).values(cliente_id=item.cliente_sugerido_id)
        await db.execute(stmt_projetos)

        # 3. Remover status 'pendente' apenas dos projetos que NÃO têm diff técnico
        stmt_status = update(GenerationProject).where(
            GenerationProject.nome_bruto_principal_id == item.nome_bruto_id,
            text("projetos_geracao.diff_pendente IS NULL OR projetos_geracao.diff_pendente = 'null'::jsonb")
        ).values(status_revisao=ReviewStatus.aprovado)
        await db.execute(stmt_status)

    elif item.motivo_pendencia == MotivoPendenciaEnum.alteracao_dado:
        # A alteração no dado técnico já foi gravada pelo ETL. 
        # A aprovação apenas limpa o aviso da tela.
        item.diff_pendente = None

    await db.commit()
    await db.refresh(item, attribute_names=["cegs_relacionados"])
    return item


async def rejeitar_pendencia(
    db: AsyncSession, item_id: int, usuario_id: UUID
) -> PendingConsolidation:
    """
    Rejeita a pendência. Para consolidacao_nome, cria um cliente isolado.
    Para alteracao_dado, mantém o diff_pendente para auditoria.
    """
    item = await _buscar_pendencia(db, item_id)

    item.status = ConsolidationStatus.rejeitado
    item.decidido_por = usuario_id
    item.decidido_em = datetime.now(timezone.utc)

    if item.motivo_pendencia == MotivoPendenciaEnum.consolidacao_nome:
        raw_name = await db.get(RawName, item.nome_bruto_id)
        if not raw_name:
            raise HTTPException(status_code=404, detail="Nome bruto não encontrado")
        
        # 1. O cliente recusa o agrupamento sugerido. Criamos um Cliente Isolado para este nome.
        novo_cliente = Client(nome_oficial=raw_name.nome_bruto)
        db.add(novo_cliente)
        await db.flush()  # Força a geração do UUID do novo_cliente no banco

        raw_name.cliente_id = novo_cliente.id

        # 2. Propagar o NOVO cliente_id para os projetos associados a este nome
        stmt_projetos = update(GenerationProject).where(
            GenerationProject.nome_bruto_principal_id == item.nome_bruto_id
        ).values(cliente_id=novo_cliente.id)
        await db.execute(stmt_projetos)

        # 3. Remover status 'pendente' apenas dos projetos que NÃO têm diff técnico
        stmt_status = update(GenerationProject).where(
            GenerationProject.nome_bruto_principal_id == item.nome_bruto_id,
            text("projetos_geracao.diff_pendente IS NULL OR projetos_geracao.diff_pendente = 'null'::jsonb")
        ).values(status_revisao=ReviewStatus.aprovado)
        await db.execute(stmt_status)

    # Se for alteracao_dado, não limpamos o diff_pendente (auditoria) e nem
    # revertemos o dado (evita loop no ETL do dia seguinte).

    await db.commit()
    await db.refresh(item, attribute_names=["cegs_relacionados"])
    return item