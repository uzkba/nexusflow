"""
Parsing da coluna de proprietários do CSV do SIGA (funções puras, sem banco).

Extraído de populate_nomes_brutos.py para que o ETL de nomes_brutos e o ETL
de projetos_geracao usem EXATAMENTE a mesma regra de leitura e a mesma
formatação do nome bruto. Se as duas implementações divergirem, o dono
principal de um projeto deixa de bater com a linha de nomes_brutos.

Coluna 'DscPropriRegimePariticipacao' (typo da própria ANEEL). Dois formatos:

  1. Antigo (com hífen e, em geral, CNPJ):
         "{pct}% para {NOME} - {CNPJ} ({REGIME})"
  2. Atual (CSV público de 2026-10, SEM CNPJ):
         "{pct}% para {NOME} ({REGIME})"
         "99.9000% para A S.A (PIE), 0.1000% para B Ltda. (PIE)"

Um ou mais proprietários por linha, separados por ", {pct}% para ". A divisão
é por esse padrão (e não por vírgula) porque nomes de empresa podem ter
vírgula. O valor literal "Não Informado" aparece sem o padrão.

DECISÃO DE NEGÓCIO (formato atual): sem CNPJ, a identidade do nome bruto é
só o nome. Proprietários distintos com o mesmo nome viram o mesmo nome_bruto.

O regime (REG/APE/PIE) não entra na identidade do nome bruto. O percentual
também não, mas é devolvido aqui para a escolha do dono principal.
"""

import html
import re
from typing import NamedTuple

_PCT = r"\d+(?:[.,]\d+)?"
_CNPJ = r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"

# Formato antigo: regex original, só com percentual decimal aceito. Ancorado
# no hífen antes do CNPJ opcional (nomes têm hífen interno, ex: "CRERAL-
# COOPERATIVA...", então não dá para dividir por "-" ou ",").
ENTRY_RE = re.compile(
    rf"(?P<pct>{_PCT})%\s*para\s*(?P<nome>.*?)\s*-\s*"
    rf"(?P<cnpj>{_CNPJ})?\s*\((?P<regime>[A-Za-z]+)\)"
)

# Formato atual: um dono por trecho, sem CNPJ. Ancorado no início e no fim do
# trecho, então parênteses e hífens dentro do nome não atrapalham.
ENTRY_SEM_CNPJ_RE = re.compile(
    rf"^(?P<pct>{_PCT})%\s*para\s*(?P<nome>.+?)\s*\((?P<regime>[A-Za-z]+)\)\s*$"
)

# Separa donos: vírgula seguida de "{pct}% para".
SPLIT_DONOS_RE = re.compile(rf",\s*(?={_PCT}%\s*para\b)")

NAO_INFORMADO_RE = re.compile(r"^n[aã]o informado$", re.IGNORECASE)

# Mesmo valor de SENTINELA_NOME em backend/app/core/constantes.py
# (backend/tests/test_parsing_proprietarios.py garante a igualdade).
NOME_NAO_INFORMADO = "Não Informado"


class Proprietario(NamedTuple):
    nome: str
    cnpj: str | None  # None = sem CNPJ (formato atual), pessoa física ou "Não Informado"
    percentual: float


def limpar_texto(texto: str) -> str:
    """Corrige entidade HTML truncada e decodifica entidades normais."""
    texto = texto.replace("&amp-", "&").replace("&amp;", "&")
    texto = html.unescape(texto)
    return " ".join(texto.split())  # normaliza espaços


def extrair_proprietarios_com_percentual(valor_bruto: str) -> list[Proprietario]:
    """
    Retorna os proprietários de uma linha do CSV, na ordem em que aparecem,
    com o percentual de cada um. Uma linha 50/50 devolve 2 itens.

    "Não Informado" devolve um único item com percentual 100 (não há
    percentual no dado, e o projeto inteiro pertence a esse "dono").
    Lista vazia = linha que não bateu com nenhum dos formatos esperados.
    """
    texto = limpar_texto(str(valor_bruto))

    if NAO_INFORMADO_RE.match(texto):
        return [Proprietario(NOME_NAO_INFORMADO, None, 100)]

    resultados = []
    for trecho in SPLIT_DONOS_RE.split(texto):
        match = ENTRY_RE.search(trecho)
        if match:
            cnpj = match.group("cnpj")
        else:
            match = ENTRY_SEM_CNPJ_RE.match(trecho)
            cnpj = None
        if not match:
            continue

        nome = " ".join(match.group("nome").split()).strip(" -")
        nome = nome.strip(" '\"")  # remove aspas soltas nas pontas (ex: '' NOME '')
        percentual = float(match.group("pct").replace(",", "."))
        resultados.append(Proprietario(nome, cnpj, percentual))
    return resultados


def extrair_proprietarios(valor_bruto: str) -> list[tuple[str, str | None]]:
    """
    Versão de compatibilidade: lista de (nome_limpo, cnpj), sem percentual.
    É o que populate_nomes_brutos.py sempre usou -- o comportamento não muda.
    """
    return [(p.nome, p.cnpj) for p in extrair_proprietarios_com_percentual(valor_bruto)]


def formatar_nome_bruto(nome: str, cnpj: str | None) -> str:
    """
    Chave textual gravada em nomes_brutos.nome_bruto: "NOME - CNPJ", ou só o
    nome quando não há CNPJ (formato atual, pessoa física e "Não Informado").
    """
    return f"{nome} - {cnpj}" if cnpj else nome
