"""
Testes de backend/app/etl/parsing_proprietarios.py (funções puras, sem banco).

O parsing foi extraído de populate_nomes_brutos.py. Estes testes garantem que:
1. a versão extraída devolve EXATAMENTE o que a implementação original
   devolvia (regressão: os 666 nomes únicos da carga de referência dependem
   disso);
2. o percentual agora é devolvido, sem alterar nada do resto.
"""

import html
import re

import pytest

from backend.app.core.constantes import SENTINELA_NOME
from backend.app.etl.parsing_proprietarios import (
    NOME_NAO_INFORMADO,
    Proprietario,
    extrair_proprietarios,
    extrair_proprietarios_com_percentual,
    formatar_nome_bruto,
    limpar_texto,
)

# ---------------------------------------------------------------------------
# Implementação ORIGINAL (cópia literal de populate_nomes_brutos.py antes da
# extração). Serve de oráculo: se alguém mexer no parsing novo e mudar o
# resultado, o teste de equivalência abaixo quebra.
# ---------------------------------------------------------------------------
_ENTRY_RE_LEGADO = re.compile(
    r"(?P<pct>\d+)%\s*para\s*(?P<nome>.*?)\s*-\s*"
    r"(?P<cnpj>\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})?\s*\((?P<regime>[A-Za-z]+)\)"
)
_NAO_INFORMADO_RE_LEGADO = re.compile(r"^n[aã]o informado$", re.IGNORECASE)


def _limpar_texto_legado(texto: str) -> str:
    texto = texto.replace("&amp-", "&").replace("&amp;", "&")
    texto = html.unescape(texto)
    return " ".join(texto.split())


def _extrair_proprietarios_legado(valor_bruto: str):
    texto = _limpar_texto_legado(str(valor_bruto))
    if _NAO_INFORMADO_RE_LEGADO.match(texto):
        return [("Não Informado", None)]
    resultados = []
    for match in _ENTRY_RE_LEGADO.finditer(texto):
        nome = " ".join(match.group("nome").split()).strip(" -")
        nome = nome.strip(" '\"")
        cnpj = match.group("cnpj")
        resultados.append((nome, cnpj))
    return resultados


CASOS = {
    "dois_donos_5050": (
        "50% para CRERAL- COOPERATIVA DE GERACAO DE ENERGIA E "
        "DESENVOLVIMENTO - 11.192.351/0001-68 (REG), 50% para HIPPO "
        "SUPERMERCADOS LTDA - 01.936.465/0001-11 (REG)"
    ),
    "dono_unico": "100% para VENTOS DE SAO CARLOS 01 ENERGIA LTDA - 12.345.678/0001-90 (PIE)",
    # A regex exige o hífen antes do CNPJ opcional; sem CNPJ sobra "NOME - (REGIME)".
    # Formato inferido da regex, não de uma linha real: confirme com os 666 nomes.
    "pessoa_fisica_sem_cnpj": "100% para JOAO DA SILVA - (APE)",
    "nao_informado": "Não Informado",
    "nao_informado_sem_acento_caixa_mista": "  nao INFORMADO ",
    "entidade_html_truncada": "100% para BELO &amp- FILHOS LTDA - 98.765.432/0001-10 (REG)",
    "entidade_html_normal": "100% para BELO &amp; FILHOS LTDA - 98.765.432/0001-10 (REG)",
    "aspas_soltas": "100% para '' EMPRESA X LTDA '' - 11.111.111/0001-11 (REG)",
    "tres_donos_percentuais_distintos": (
        "60% para ALFA SA - 11.111.111/0001-11 (REG), "
        "30% para BETA LTDA - 22.222.222/0001-22 (REG), "
        "10% para GAMA ME - 33.333.333/0001-33 (APE)"
    ),
    "padrao_nao_reconhecido": "texto sem o formato esperado",
    "vazio": "",
}


@pytest.mark.parametrize("nome_caso", list(CASOS))
def test_extrair_proprietarios_identico_ao_original(nome_caso):
    valor = CASOS[nome_caso]
    assert extrair_proprietarios(valor) == _extrair_proprietarios_legado(valor)


@pytest.mark.parametrize("nome_caso", list(CASOS))
def test_limpar_texto_identico_ao_original(nome_caso):
    valor = CASOS[nome_caso]
    assert limpar_texto(valor) == _limpar_texto_legado(valor)


def test_percentual_de_dois_donos_5050():
    donos = extrair_proprietarios_com_percentual(CASOS["dois_donos_5050"])
    assert [d.percentual for d in donos] == [50, 50]
    assert donos[0].cnpj == "11.192.351/0001-68"
    assert donos[1].nome == "HIPPO SUPERMERCADOS LTDA"


def test_percentuais_distintos_preservam_a_ordem_da_string():
    donos = extrair_proprietarios_com_percentual(CASOS["tres_donos_percentuais_distintos"])
    assert [(d.nome, d.percentual) for d in donos] == [
        ("ALFA SA", 60),
        ("BETA LTDA", 30),
        ("GAMA ME", 10),
    ]


def test_pessoa_fisica_sem_cnpj_tem_cnpj_none_e_percentual():
    donos = extrair_proprietarios_com_percentual(CASOS["pessoa_fisica_sem_cnpj"])
    assert donos == [Proprietario("JOAO DA SILVA", None, 100)]


def test_nao_informado_vira_um_dono_com_percentual_100():
    for chave in ("nao_informado", "nao_informado_sem_acento_caixa_mista"):
        assert extrair_proprietarios_com_percentual(CASOS[chave]) == [
            Proprietario("Não Informado", None, 100)
        ]


def test_padrao_nao_reconhecido_devolve_lista_vazia():
    assert extrair_proprietarios_com_percentual(CASOS["padrao_nao_reconhecido"]) == []
    assert extrair_proprietarios_com_percentual(CASOS["vazio"]) == []


def test_entidade_html_truncada_e_corrigida():
    (dono,) = extrair_proprietarios_com_percentual(CASOS["entidade_html_truncada"])
    assert dono.nome == "BELO & FILHOS LTDA"


def test_aspas_soltas_nas_pontas_sao_removidas():
    (dono,) = extrair_proprietarios_com_percentual(CASOS["aspas_soltas"])
    assert dono.nome == "EMPRESA X LTDA"


def test_formatar_nome_bruto_com_e_sem_cnpj():
    assert formatar_nome_bruto("ALFA SA", "11.111.111/0001-11") == "ALFA SA - 11.111.111/0001-11"
    assert formatar_nome_bruto("JOAO DA SILVA", None) == "JOAO DA SILVA"
    assert formatar_nome_bruto("Não Informado", None) == "Não Informado"


def test_nome_bruto_formatado_bate_com_o_formato_gravado_em_nomes_brutos():
    # Formato histórico de nomes_brutos.nome_bruto: f"{nome} - {cnpj}" / nome
    for valor in CASOS.values():
        for nome, cnpj in _extrair_proprietarios_legado(valor):
            esperado = f"{nome} - {cnpj}" if cnpj else nome
            assert formatar_nome_bruto(nome, cnpj) == esperado


def test_nome_nao_informado_igual_ao_do_sentinela():
    assert NOME_NAO_INFORMADO == SENTINELA_NOME