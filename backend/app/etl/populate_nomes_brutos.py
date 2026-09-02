"""
Pipeline: popular nomes_brutos a partir da primeira carga do CSV do SIGA.

DESCOBERTAS DA INSPECAO REAL DO ARQUIVO (nao assuma nada disso sem reconferir
se o layout do CSV mudar em cargas futuras):

1. Coluna real (CSV publico do CKAN) e' 'DscPropriRegimePariticipacao'
   (nome com erro de digitacao da propria ANEEL - "Pariticipacao").
   NAO existe coluna separada de CNPJ.

2. Essa coluna e' uma STRING COMPOSTA, com um ou mais proprietarios por
   linha, formato:
       "{pct}% para {NOME} - {CNPJ} ({REGIME})"
   separados por ", " quando ha mais de um dono no mesmo empreendimento.
   Exemplo real:
       "50% para CRERAL- COOPERATIVA DE GERACAO DE ENERGIA E
        DESENVOLVIMENTO - 11.192.351/0001-68 (REG), 50% para HIPPO
        SUPERMERCADOS LTDA - 01.936.465/0001-11 (REG)"

3. total de linhas no CSV: 25133
   valores unicos da coluna INTEIRA (sem parsing): 5593
   -- nenhum dos dois bate com o "25258" que estava no checklist original.
   O numero de referencia real so vai existir DEPOIS de rodar o parsing
   abaixo -- nao assuma 25258 nem 5593 como gabarito de validacao.

4. Encoding real e' UTF-8, nao latin-1 (latin-1 gerava mojibake tipo
   "IndÃºstria"). Corrigido abaixo.

5. Ha entidades HTML corrompidas no dado (ex: "&amp-" no lugar de "&amp;",
   provavelmente por troca de ';' por '-' em processamento anterior).
   Tratado via limpeza antes do parsing.

DECISAO CONFIRMADA COM O USUARIO: dividir por proprietario individual
(nome + CNPJ), nao manter a string composta inteira. O regime (REG/APE/PIE)
e o percentual NAO entram na identidade do nome_bruto -- sao metadados de
participacao que podem variar por projeto mesmo pro mesmo proprietario,
entao nao fazem parte da chave.

PENDENCIA (ainda nao confirmada): nome exato da coluna pode ter variacoes
entre cargas do CKAN -- validar se 'DscPropriRegimePariticipacao' e' estavel
entre execucoes antes de deixar isso rodando sem supervisao.
"""

import argparse
import asyncio
import html
import logging
import re
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

# Ajustar conforme localizacao real no projeto nexusflow
from backend.app.model.models import RawName
from backend.app.db.session import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("populate_nomes_brutos")

COLUNA_PROPRIETARIO = "DscPropriRegimePariticipacao"
COLUNA_ORIGEM = "SigTipoGeracao"
COLUNA_FASE = "DscFaseUsina"

# Filtros de negocio ja fechados em outra parte do projeto (Transform do
# ETL principal de projetos_geracao) -- REPLICADOS aqui porque nomes_brutos
# so' deve conter proprietarios de empreendimentos que vao efetivamente
# entrar no dashboard. Se esses filtros mudarem em um lugar, tem que mudar
# nos dois (idealmente extrair pra config compartilhada depois).
ORIGENS_PERMITIDAS = {"UFV", "EOL"}  # Solar fotovoltaica, Eolica
FASE_PERMITIDA = "Construção não iniciada"

# Ancorado no padrao de CNPJ (fixo: XX.XXX.XXX/XXXX-XX), nao em split por
# virgula ou hifen -- nomes de empresa tem hifen interno (ex: "CRERAL-
# COOPERATIVA..."), entao dividir por "-" ou "," quebraria nomes reais.
ENTRY_RE = re.compile(
    r"(?P<pct>\d+)%\s*para\s*(?P<nome>.*?)\s*-\s*"
    r"(?P<cnpj>\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})?\s*\((?P<regime>[A-Za-z]+)\)"
)

# Pessoa fisica nao tem CNPJ no dataset da ANEEL -- o grupo cnpj acima e'
# opcional por causa disso (nao e' erro de formato, e' a estrutura real).

NAO_INFORMADO_RE = re.compile(r"^n[aã]o informado$", re.IGNORECASE)


def limpar_texto(texto: str) -> str:
    """Corrige entidade HTML truncada e decodifica entidades normais."""
    texto = texto.replace("&amp-", "&").replace("&amp;", "&")
    texto = html.unescape(texto)
    return " ".join(texto.split())  # normaliza espacos


def extrair_proprietarios(valor_bruto: str) -> list[tuple[str, str]]:
    """
    Retorna lista de (nome_limpo, cnpj) para uma linha do CSV.
    Uma linha com 2 proprietarios (ex: split 50/50) retorna 2 tuplas.
    """
    texto = limpar_texto(str(valor_bruto))

    if NAO_INFORMADO_RE.match(texto):
        return [("Não Informado", None)]

    resultados = []
    for match in ENTRY_RE.finditer(texto):
        nome = " ".join(match.group("nome").split()).strip(" -")
        nome = nome.strip(" '\"")  # remove aspas soltas nas pontas (ex: '' NOME '')
        cnpj = match.group("cnpj")  # None para pessoa fisica (sem CNPJ no dataset)
        resultados.append((nome, cnpj))
    return resultados


def extrair_valores_unicos(csv_path: str) -> list[str]:
    """
    Le o CSV, faz parsing de todos os proprietarios individuais (podem ser
    varios por linha) e retorna lista de nome_bruto unicos no formato
    "NOME - CNPJ".
    """
    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        logger.warning("UTF-8 falhou, tentando latin-1 como fallback -- CONFIRME visualmente que nao gera mojibake")
        df = pd.read_csv(csv_path, sep=";", encoding="latin-1", low_memory=False)

    for col in (COLUNA_PROPRIETARIO, COLUNA_ORIGEM, COLUNA_FASE):
        if col not in df.columns:
            raise ValueError(
                f"Coluna '{col}' nao encontrada. Colunas disponiveis: {list(df.columns)}"
            )

    total_linhas_csv = len(df)

    df_filtrado = df[
        df[COLUNA_ORIGEM].isin(ORIGENS_PERMITIDAS)
        & (df[COLUNA_FASE] == FASE_PERMITIDA)
    ]

    logger.info(
        "Filtro de negocio aplicado -- origem %s + fase '%s': %d de %d linhas restantes",
        sorted(ORIGENS_PERMITIDAS),
        FASE_PERMITIDA,
        len(df_filtrado),
        total_linhas_csv,
    )

    serie = df_filtrado[COLUNA_PROPRIETARIO].dropna()

    linhas_sem_match = 0
    pares_unicos: set[tuple[str, str]] = set()

    for valor in serie:
        proprietarios = extrair_proprietarios(valor)
        if not proprietarios:
            linhas_sem_match += 1
            continue
        pares_unicos.update(proprietarios)

    if linhas_sem_match:
        logger.warning(
            "%d linha(s) nao bateram com o padrao regex esperado -- "
            "REVISAR MANUALMENTE, provavelmente formato diferente do usual",
            linhas_sem_match,
        )

    # CNPJ ausente = pessoa fisica (dataset da ANEEL nao expoe CPF) ou o
    # literal "Nao Informado". Nesses casos o nome_bruto fica so' o nome --
    # ATENCAO: duas pessoas fisicas homonimas vao colidir no mesmo
    # nome_bruto, isso e' limitacao do dado de origem, nao do parsing.
    pessoas_fisicas_sem_cnpj = sum(1 for _, cnpj in pares_unicos if cnpj is None and _ != "Não Informado")
    if pessoas_fisicas_sem_cnpj:
        logger.info(
            "%d nome(s) de pessoa fisica sem CNPJ (dataset da ANEEL nao expoe CPF) -- "
            "risco de colisao entre homonimos, sem forma de desambiguar com este dado",
            pessoas_fisicas_sem_cnpj,
        )

    nomes_brutos = sorted(
        f"{nome} - {cnpj}" if cnpj else nome
        for nome, cnpj in pares_unicos
    )

    logger.info("Total de linhas no CSV (bruto, todas as origens/fases): %d", total_linhas_csv)
    logger.info("Total de linhas apos filtro origem+fase, com proprietario preenchido: %d", len(serie))
    logger.info("Pares (nome, cnpj) unicos apos parsing: %d", len(nomes_brutos))

    return nomes_brutos


async def popular_nomes_brutos(
    session: AsyncSession,
    valores_unicos: list[str],
    timestamp_carga: datetime,
) -> dict:
    """
    Insere cada nome_bruto de forma idempotente via ON CONFLICT DO NOTHING.
    Isso e' especifico pra "primeira carga" -- nao incrementa
    total_ocorrencias em re-execucoes do mesmo arquivo (esse e' o
    comportamento do fluxo de cargas recorrentes, nao deste script).
    """
    inseridos = 0
    ja_existiam = 0

    for nome in valores_unicos:
        stmt = (
            pg_insert(RawName)
            .values(
                nome_bruto=nome,
                primeira_ocorrencia=timestamp_carga,
                ultima_ocorrencia=timestamp_carga,
                total_ocorrencias=1,
                cliente_id=None,  # aguardando aprovacao de vinculo (Fase 2/3)
            )
            .on_conflict_do_nothing(index_elements=["nome_bruto"])
            .returning(RawName.id)
        )
        result = await session.execute(stmt)
        if result.first() is not None:
            inseridos += 1
        else:
            ja_existiam += 1

    await session.commit()
    return {"inseridos": inseridos, "ja_existiam": ja_existiam}


async def validar_contagem_final(session: AsyncSession, esperado: int) -> bool:
    result = await session.execute(select(RawName.id))
    total_no_banco = len(result.all())

    logger.info("Total em nomes_brutos apos execucao: %d", total_no_banco)
    logger.info("Total esperado (passado via --esperado): %d", esperado)

    if total_no_banco != esperado:
        logger.warning(
            "DIVERGENCIA: banco tem %d, esperado %d (diferenca: %d). "
            "Investigar antes de seguir para Fase 2.",
            total_no_banco,
            esperado,
            total_no_banco - esperado,
        )
        return False

    logger.info("Contagem validada com sucesso.")
    return True


async def main(csv_path: str, esperado: int | None):
    timestamp_carga = datetime.now(timezone.utc)

    valores_unicos = extrair_valores_unicos(csv_path)

    if esperado is None:
        logger.warning(
            "Nenhum --esperado informado. Rode uma vez, veja o total logado "
            "acima, e use esse numero como referencia daqui pra frente -- "
            "NAO existe ainda um numero de validacao confiavel pra este "
            "pipeline (25258 do checklist original estava errado)."
        )

    async with AsyncSessionLocal() as session:
        stats = await popular_nomes_brutos(session, valores_unicos, timestamp_carga)
        logger.info(
            "Execucao concluida -- inseridos: %d | ja existiam (idempotencia): %d",
            stats["inseridos"],
            stats["ja_existiam"],
        )

        if esperado is not None:
            ok = await validar_contagem_final(session, esperado)
            if not ok:
                raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="Caminho para o CSV bruto do SIGA")
    parser.add_argument(
        "--esperado",
        type=int,
        default=None,
        help="Contagem esperada de nomes unicos. Sem valor confiavel ainda -- "
        "rode sem esse parametro na primeira vez pra descobrir o numero real.",
    )
    args = parser.parse_args()

    asyncio.run(main(args.csv, args.esperado))