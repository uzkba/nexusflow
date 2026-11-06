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
from sqlalchemy import func, or_, select, update, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.model.models import PendingConsolidation, RawName, GenerationProject, Client
from backend.app.enum import ConsolidationStatus
from backend.app.enum.projeto_geracao import ReviewStatus
from backend.app.enum.consolidacao import MotivoPendenciaEnum
from backend.app.schemas.filtros_schema import FiltrosQuery
# Mesmas condições de filtro da sidebar usadas na Visão Geral (regra em um só lugar)
from backend.app.services.dashboard_service import _condicoes as condicoes_filtros


def _sem_diff_tecnico():
    """
    Projeto sem diff técnico pendente: diff_pendente é SQL NULL ou JSON null.

    Usa or_() para que a condição seja SEMPRE agrupada entre parênteses ao ser
    combinada com outras no WHERE. Um text() solto com "A OR B" dentro de um
    AND vira "X AND A OR B" (AND tem precedência sobre OR) e atinge linhas de
    outros projetos.
    """
    return or_(
        GenerationProject.diff_pendente.is_(None),
        text("projetos_geracao.diff_pendente = 'null'::jsonb"),
    )


async def _listar(
    db: AsyncSession,
    filtros: FiltrosQuery | None,
    statuses: list[ConsolidationStatus],
    apenas_consolidacao_nome: bool = False,
    mais_recentes_primeiro: bool = False,
) -> list[dict]:
    """
    Retorna as pendências (ou decisões) enriquecidas com agregados (UFs, municípios,
    total de projetos, potência total) e os nomes de domínio.

    Com `filtros` (sidebar), só entram as pendências que têm ao menos um projeto
    ligado que atenda aos filtros. Os agregados do card continuam somando TODOS os
    projetos da pendência, porque aprovar uma consolidação afeta todos eles.
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
        .where(PendingConsolidation.status.in_(statuses))
    )

    if apenas_consolidacao_nome:
        stmt = stmt.where(
            PendingConsolidation.motivo_pendencia == MotivoPendenciaEnum.consolidacao_nome
        )

    if filtros is not None:
        # Projeto ligado à pendência: por nome (consolidação) ou por CEG (alteração)
        projeto_da_pendencia = or_(
            GenerationProject.nome_bruto_principal_id == PendingConsolidation.nome_bruto_id,
            GenerationProject.ceg == PendingConsolidation.ceg,
        )

        # Filtros de projeto (origem, nome, uf, município, ano). O cliente é tratado abaixo.
        condicoes = condicoes_filtros(filtros.model_copy(update={"cliente": None}))
        if condicoes:
            stmt = stmt.where(
                select(GenerationProject.ceg)
                .where(projeto_da_pendencia, *condicoes)
                .correlate(PendingConsolidation)
                .exists()
            )

        # Cliente: casa com o cliente SUGERIDO (consolidação de nome, em que os projetos
        # ainda não têm cliente) ou com o cliente já vinculado aos projetos (alteração de dado)
        if filtros.cliente:
            stmt = stmt.where(
                or_(
                    PendingConsolidation.cliente_sugerido_id == filtros.cliente,
                    select(GenerationProject.ceg)
                    .where(projeto_da_pendencia, GenerationProject.cliente_id == filtros.cliente)
                    .correlate(PendingConsolidation)
                    .exists(),
                )
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

    if mais_recentes_primeiro:
        # Histórico de decisões: a mais recente primeiro
        epoca = datetime.min.replace(tzinfo=timezone.utc)
        return sorted(
            resultados_finais,
            key=lambda x: x["decidido_em"] or epoca,
            reverse=True,
        )

    # Ordena alfabeticamente pelo nome sugerido para organizar os grupos na tela
    return sorted(
        resultados_finais,
        key=lambda x: (x["cliente_sugerido_nome"] or "", x["nome_bruto"] or "")
    )


async def listar_pendentes(
    db: AsyncSession, filtros: FiltrosQuery | None = None
) -> list[dict]:
    """Pendências abertas (fila de revisão)."""
    return await _listar(db, filtros, [ConsolidationStatus.pendente])


async def listar_decididas(
    db: AsyncSession,
    filtros: FiltrosQuery | None = None,
    decisao: ConsolidationStatus | None = None,
) -> list[dict]:
    """
    Histórico de consolidações de nome já decididas (aprovadas e/ou rejeitadas),
    para permitir reabrir ou inverter a decisão. `decisao` restringe a um dos status.
    """
    statuses = (
        [decisao]
        if decisao in (ConsolidationStatus.aprovado, ConsolidationStatus.rejeitado)
        else [ConsolidationStatus.aprovado, ConsolidationStatus.rejeitado]
    )
    return await _listar(
        db, filtros, statuses, apenas_consolidacao_nome=True, mais_recentes_primeiro=True
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


async def _buscar_decidida(db: AsyncSession, item_id: int) -> PendingConsolidation:
    """Busca uma consolidação de nome JÁ decidida (aprovada ou rejeitada)."""
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
    if item.status == ConsolidationStatus.pendente:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Pendência ainda não foi decidida",
        )
    if item.motivo_pendencia != MotivoPendenciaEnum.consolidacao_nome:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Só é possível reabrir consolidações de nome",
        )
    return item


async def _aplicar_aprovacao(
    db: AsyncSession, item: PendingConsolidation, usuario_id: UUID
) -> None:
    """Efeitos da aprovação. NÃO faz commit (quem chama decide)."""
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
            _sem_diff_tecnico(),
        ).values(status_revisao=ReviewStatus.aprovado)
        await db.execute(stmt_status)

    elif item.motivo_pendencia == MotivoPendenciaEnum.alteracao_dado:
        # A alteração no dado técnico já foi gravada pelo ETL. 
        # A aprovação apenas limpa o aviso da tela.
        item.diff_pendente = None


async def _aplicar_rejeicao(
    db: AsyncSession, item: PendingConsolidation, usuario_id: UUID
) -> None:
    """Efeitos da rejeição. NÃO faz commit (quem chama decide)."""
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

        # 3. Marcar como 'rejeitado' os projetos que NÃO têm diff técnico (os que têm diff
        #    continuam pendentes, aguardando a revisão do dado técnico)
        stmt_status = update(GenerationProject).where(
            GenerationProject.nome_bruto_principal_id == item.nome_bruto_id,
            _sem_diff_tecnico(),
        ).values(status_revisao=ReviewStatus.rejeitado)
        await db.execute(stmt_status)

    # Se for alteracao_dado, não limpamos o diff_pendente (auditoria) e nem
    # revertemos o dado (evita loop no ETL do dia seguinte).


async def _remover_cliente_isolado_se_orfao(
    db: AsyncSession, cliente_id: UUID, nome_bruto: str
) -> None:
    """
    Apaga o cliente criado por uma rejeição (nome_oficial == nome bruto), mas só se
    ninguém mais o referenciar. Clientes candidatos (compartilhados entre vários nomes)
    nunca são apagados.
    """
    cliente = await db.get(Client, cliente_id)
    if cliente is None or cliente.nome_oficial != nome_bruto:
        return

    referencias = 0
    for coluna, tabela in (
        (RawName.cliente_id, RawName),
        (GenerationProject.cliente_id, GenerationProject),
        (PendingConsolidation.cliente_sugerido_id, PendingConsolidation),
    ):
        total = await db.scalar(
            select(func.count()).select_from(tabela).where(coluna == cliente_id)
        )
        referencias += total or 0

    if referencias == 0:
        await db.delete(cliente)
        await db.flush()


async def _desfazer_decisao(db: AsyncSession, item: PendingConsolidation) -> None:
    """
    Volta uma consolidação de nome decidida ao estado pendente, desfazendo os efeitos
    da aprovação ou da rejeição. NÃO faz commit (quem chama decide).
    """
    raw_name = await db.get(RawName, item.nome_bruto_id)
    if not raw_name:
        raise HTTPException(status_code=404, detail="Nome bruto não encontrado")

    cliente_atual = raw_name.cliente_id
    era_rejeicao = item.status == ConsolidationStatus.rejeitado

    # 1. Projetos do nome: tira o cliente e devolve o status 'pendente'
    #    (os que têm diff técnico nunca foram alterados pela decisão)
    if cliente_atual is not None:
        await db.execute(
            update(GenerationProject)
            .where(
                GenerationProject.nome_bruto_principal_id == item.nome_bruto_id,
                GenerationProject.cliente_id == cliente_atual,
            )
            .values(cliente_id=None)
        )
    await db.execute(
        update(GenerationProject)
        .where(
            GenerationProject.nome_bruto_principal_id == item.nome_bruto_id,
            _sem_diff_tecnico(),
        )
        .values(status_revisao=ReviewStatus.pendente)
    )

    # 2. Nome bruto volta a ficar sem cliente
    raw_name.cliente_id = None
    await db.flush()

    # 3. Rejeição criou um cliente isolado: remove se ficou órfão
    if era_rejeicao and cliente_atual is not None:
        await _remover_cliente_isolado_se_orfao(db, cliente_atual, raw_name.nome_bruto)

    # 4. A pendência volta para a fila
    item.status = ConsolidationStatus.pendente
    item.decidido_por = None
    item.decidido_em = None


async def aprovar_pendencia(
    db: AsyncSession, item_id: int, usuario_id: UUID
) -> PendingConsolidation:
    """
    Aprova a pendência. Aplica as mudanças no banco dependendo do motivo.
    """
    item = await _buscar_pendencia(db, item_id)
    await _aplicar_aprovacao(db, item, usuario_id)

    await db.commit()
    await db.refresh(item, attribute_names=["cegs_relacionados"])
    return item


async def rejeitar_pendencia(
    db: AsyncSession, item_id: int, usuario_id: UUID
) -> PendingConsolidation:
    """
    Rejeita a pendência. Para consolidacao_nome, cria um cliente isolado e marca os
    projetos como status_revisao='rejeitado' (visível na Base de Dados).
    Para alteracao_dado, mantém o diff_pendente para auditoria.
    """
    item = await _buscar_pendencia(db, item_id)
    await _aplicar_rejeicao(db, item, usuario_id)

    await db.commit()
    await db.refresh(item, attribute_names=["cegs_relacionados"])
    return item


async def reabrir_pendencia(db: AsyncSession, item_id: int) -> PendingConsolidation:
    """
    Desfaz uma decisão (aprovação ou rejeição) de consolidação de nome: a pendência
    volta para a fila e os projetos voltam a ficar pendentes e sem cliente.
    """
    item = await _buscar_decidida(db, item_id)
    await _desfazer_decisao(db, item)

    await db.commit()
    await db.refresh(item, attribute_names=["cegs_relacionados"])
    return item


async def inverter_decisao(
    db: AsyncSession, item_id: int, usuario_id: UUID
) -> PendingConsolidation:
    """
    Troca a decisão numa única transação: aprovada vira rejeitada e vice-versa.
    Se algo falhar no meio, nada é gravado.
    """
    item = await _buscar_decidida(db, item_id)
    era_aprovada = item.status == ConsolidationStatus.aprovado

    await _desfazer_decisao(db, item)
    if era_aprovada:
        await _aplicar_rejeicao(db, item, usuario_id)
    else:
        await _aplicar_aprovacao(db, item, usuario_id)

    await db.commit()
    await db.refresh(item, attribute_names=["cegs_relacionados"])
    return item