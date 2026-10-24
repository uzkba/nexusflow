"""
Parsing da coluna de proprietários do CSV do SIGA (funções puras, sem banco).

Extraído de populate_nomes_brutos.py para que o ETL de nomes_brutos e o ETL
de projetos_geracao usem EXATAMENTE a mesma regra de leitura e a mesma
formatação do nome bruto. Se as duas implementações divergirem, o dono
principal de um projeto deixa de bater com a linha de nomes_brutos.

Formato real da coluna 'DscPropriRegimePariticipacao' (typo da própria ANEEL):

    "{pct}% para {NOME} - {CNPJ} ({REGIME})"

com um ou mais proprietários por linha, separados por ", ". Pessoa física não
tem CNPJ no dataset. O valor literal "Não Informado" aparece sem o padrão.

O regime (REG/APE/PIE) não entra na identidade do nome bruto. O percentual
também não, mas é devolvido aqui para a escolha do dono principal.
"""

import html
import re
from typing import NamedTuple

# Ancorado no padrão de CNPJ (fixo: XX.XXX.XXX/XXXX-XX), não em split por
# vírgula ou hífen -- nomes de empresa têm hífen interno (ex: "CRERAL-
# COOPERATIVA..."), então dividir por "-" ou "," quebraria nomes reais.
ENTRY_RE = re.compile(
    r"(?P<pct>\d+)%\s*para\s*(?P<nome>.*?)\s*-\s*"
    r"(?P<cnpj>\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})?\s*\((?P<regime>[A-Za-z]+)\)"
)

NAO_INFORMADO_RE = re.compile(r"^n[aã]o informado$", re.IGNORECASE)

# Mesmo valor de SENTINELA_NOME em backend/app/core/constantes.py
# (backend/tests/test_parsing_proprietarios.py garante a igualdade).
NOME_NAO_INFORMADO = "Não Informado"


class Proprietario(NamedTuple):
    nome: str
    cnpj: str | None  # None = pessoa física ou "Não Informado"
    percentual: int


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
    Lista vazia = linha que não bateu com o padrão esperado.
    """
    texto = limpar_texto(str(valor_bruto))

    if NAO_INFORMADO_RE.match(texto):
        return [Proprietario(NOME_NAO_INFORMADO, None, 100)]

    resultados = []
    for match in ENTRY_RE.finditer(texto):
        nome = " ".join(match.group("nome").split()).strip(" -")
        nome = nome.strip(" '\"")  # remove aspas soltas nas pontas (ex: '' NOME '')
        resultados.append(
            Proprietario(nome, match.group("cnpj"), int(match.group("pct")))
        )
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
    nome quando não há CNPJ (pessoa física e "Não Informado").
    """
    return f"{nome} - {cnpj}" if cnpj else nome