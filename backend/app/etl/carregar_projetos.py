"""
Orquestrador do ETL de projetos de geração.
Lê o CSV, filtra regras de negócio, transforma via pipeline puro, 
mapeia as chaves com `nomes_brutos`, e faz o upsert transacional.
"""
import argparse
import asyncio
import logging

import pandas as pd
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constantes import SENTINELA_CLIENTE_ID
from backend.app.db.session import AsyncSessionLocal
from backend.app.model.models import GenerationProject, RawName
from backend.app.enum.projeto_geracao import ReviewStatus

from backend.app.etl.transform_projetos import transformar_projeto
from backend.app.etl.upsert_projetos_geracao import upsert_projetos_geracao

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("carregar_projetos")

ORIGENS_PERMITIDAS = {"UFV", "EOL"}
FASE_PERMITIDA = "Construção não iniciada"


async def _carregar_mapeamento_nomes(session: AsyncSession, nomes_buscados: set[str]) -> dict:
    """Busca os RawNames necessários e devolve dict {nome_bruto: RawName}."""
    stmt = select(RawName).where(RawName.nome_bruto.in_(nomes_buscados))
    resultado = await session.execute(stmt)
    return {rn.nome_bruto: rn for rn in resultado.scalars()}


MIN_CEGS_CSV = 20_000
MAX_FRACAO_REMOVIDA = 0.30  # trava contra CSV truncado ou filtro quebrado


async def _reconciliar_removidos(session: AsyncSession, df, df_filtrado) -> dict:
    ceg_csv = set(df["CodCEG"].dropna().astype(str).str.strip())
    ceg_elegiveis = set(df_filtrado["CodCEG"].astype(str).str.strip())

    if len(ceg_csv) < MIN_CEGS_CSV:
        raise RuntimeError(f"CSV com só {len(ceg_csv)} CEGs; reconciliação abortada.")

    cegs_banco = set((await session.scalars(select(GenerationProject.ceg))).all())
    ausentes = cegs_banco - ceg_csv
    fora_filtro = (cegs_banco & ceg_csv) - ceg_elegiveis
    voltaram = cegs_banco & ceg_elegiveis

    saindo = len(ausentes) + len(fora_filtro)
    if cegs_banco and saindo / len(cegs_banco) > MAX_FRACAO_REMOVIDA:
        raise RuntimeError(
            f"Reconciliação abortada: {saindo} de {len(cegs_banco)} projetos "
            f"sairiam (limite {MAX_FRACAO_REMOVIDA:.0%})."
        )

    async def _marcar(cegs: set, motivo: str):
        if cegs:
            await session.execute(
                update(GenerationProject)
                .where(
                    GenerationProject.ceg.in_(cegs),
                    GenerationProject.removido_da_fonte_em.is_(None),
                )
                .values(removido_da_fonte_em=func.now(), motivo_remocao=motivo)
            )

    await _marcar(ausentes, "ausente_no_csv")
    await _marcar(fora_filtro, "fora_do_filtro")

    if voltaram:
        await session.execute(
            update(GenerationProject)
            .where(
                GenerationProject.ceg.in_(voltaram),
                GenerationProject.removido_da_fonte_em.is_not(None),
            )
            .values(removido_da_fonte_em=None, motivo_remocao=None)
        )

    return {"ausentes": len(ausentes), "fora_filtro": len(fora_filtro), "voltaram": len(voltaram)}


async def orquestrar_carga(csv_path: str, esperado: int | None):
    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        logger.warning("UTF-8 falhou, tentando latin-1...")
        df = pd.read_csv(csv_path, sep=";", encoding="latin-1", low_memory=False)

    # 1. Filtros de Negócio
    df_filtrado = df[
        df["SigTipoGeracao"].isin(ORIGENS_PERMITIDAS)
        & (df["DscFaseUsina"] == FASE_PERMITIDA)
    ]
    
    logger.info(f"Filtro aplicado: {len(df_filtrado)} registros retidos de {len(df)} totais.")
    
    # Validações de integridade do dataset
    if df_filtrado["CodCEG"].isnull().any():
        raise ValueError("ERRO: Existem linhas com CEG nulo/ausente no recorte.")
        
    if df_filtrado["CodCEG"].duplicated().any():
        duplicados = df_filtrado[df_filtrado["CodCEG"].duplicated()]["CodCEG"].tolist()
        raise ValueError(f"ERRO: Existem CEGs duplicados no dataset: {duplicados}")
        
    if esperado is not None and len(df_filtrado) != esperado:
        raise ValueError(f"ERRO: Esperava {esperado} registros, mas o filtro resultou em {len(df_filtrado)}.")
        
    # 2. Transformação pura
    registros_transformados = []
    nomes_necessarios = set()
    
    for _, row in df_filtrado.iterrows():
        # Converte valores NaT/NaN do pandas para None
        dict_row = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
        
        projeto = transformar_projeto(dict_row)
        nomes_necessarios.add(projeto["nome_bruto_principal_str"])
        registros_transformados.append(projeto)
        
    async with AsyncSessionLocal() as session:
        # 3. Lookup de Nomes Brutos
        mapa_nomes = await _carregar_mapeamento_nomes(session, nomes_necessarios)
        nomes_faltantes = nomes_necessarios - set(mapa_nomes.keys())
        
        if nomes_faltantes:
            raise RuntimeError(
                f"ETL Abortado: {len(nomes_faltantes)} donos principais não existem na tabela nomes_brutos. "
                f"Você precisa rodar populate_nomes_brutos primeiro. Faltantes (amostra): {list(nomes_faltantes)[:5]}"
            )
            
        # Para fins de log: contar quantos CEGs já existem no banco antes do upsert
        cegs = [r["ceg"] for r in registros_transformados]
        stmt_cegs = select(GenerationProject.ceg).where(GenerationProject.ceg.in_(cegs))
        cegs_no_banco = (await session.scalars(stmt_cegs)).all()
        total_existentes = len(cegs_no_banco)
        total_inseridos = len(registros_transformados) - total_existentes
        
        # 4. Enriquecer o payload com as FKs
        lote_final = []
        for reg in registros_transformados:
            nome_str = reg.pop("nome_bruto_principal_str")
            raw_name = mapa_nomes[nome_str]
            
            reg["nome_bruto_principal_id"] = raw_name.id
            reg["cliente_id"] = raw_name.cliente_id
            
            # Regra de negócio: se for o sentinela, o projeto nasce como 'aprovado'
            if raw_name.cliente_id == SENTINELA_CLIENTE_ID:
                reg["status_revisao"] = ReviewStatus.aprovado
                
            lote_final.append(reg)
            
        # 5. Executar Upsert em bloco e Commitar
        await upsert_projetos_geracao(session, lote_final)
        resumo_recon = await _reconciliar_removidos(session, df, df_filtrado)
        await session.commit()
        logger.info(f"Reconciliação: {resumo_recon}")
        
        # 6. Avaliar o que aconteceu (o upsert modifica o dict do lote_final in-place com o diff)
        total_com_diff = sum(1 for r in lote_final if r.get("diff_pendente"))
        total_sem_mudanca = total_existentes - total_com_diff
        
        logger.info("====== RESUMO DA CARGA ======")
        logger.info(f"Total de projetos elegíveis : {len(lote_final)}")
        logger.info(f" -> Novos Inseridos         : {total_inseridos}")
        logger.info(f" -> Atualizados (com diff)  : {total_com_diff}")
        logger.info(f" -> Ignorados (sem mudança) : {total_sem_mudanca}")
        logger.info("=============================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL principal de carga de projetos")
    parser.add_argument("--csv", required=True, help="Caminho para o arquivo CSV.")
    parser.add_argument("--esperado", type=int, default=None, help="Validação de segurança: quantidade exata de linhas esperadas após o filtro.")
    args = parser.parse_args()
    
    asyncio.run(orquestrar_carga(args.csv, args.esperado))