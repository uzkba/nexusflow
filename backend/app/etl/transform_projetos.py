"""
Funções puras para transformação de dados de projetos de geração.
Nenhuma dependência de banco de dados ou estado externo.
"""
import re
from typing import Any

from backend.app.etl.parsing_proprietarios import (
    extrair_proprietarios_com_percentual,
    formatar_nome_bruto,
)

# Mapeamento de origens definido nos requisitos
MAPA_ORIGEM = {
    "UFV": "Solar",
    "EOL": "Eólica"
}

def extrair_ano_iso(data_str: str) -> int:
    """Extrai o ano de uma string de data. Assume formato contendo ano em 4 dígitos."""
    if not data_str or str(data_str).strip() == "":
        raise ValueError("Data de início da vigência ausente ou vazia.")
    
    # Tenta casar os 4 primeiros dígitos como ano (padrão ISO YYYY-MM-DD ou DD/MM/YYYY)
    match = re.search(r"\b(19|20)\d{2}\b", str(data_str))
    if not match:
        raise ValueError(f"Não foi possível identificar um ano válido em: {data_str}")
    return int(match.group(0))


def parse_float(valor: Any) -> float | None:
    """Converte string com vírgula decimal para float padrão."""
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        raise ValueError(f"Falha ao converter para número: {valor}")


def extrair_dono_principal(valor_proprietarios: str) -> str:
    """
    Desempate para multi-donos:
    1. Maior percentual.
    2. Empate: Ordem alfabética do CNPJ (vazio antes de preenchido).
    3. Empate: Ordem alfabética do Nome.
    Devolve a string formatada "Nome - CNPJ" do vencedor.
    """
    proprietarios = extrair_proprietarios_com_percentual(valor_proprietarios)
    if not proprietarios:
        raise ValueError(f"Nenhum proprietário extraído de: {valor_proprietarios}")

    # sorted com chave composta. Percentual negativo para ordenar decrescente.
    proprietarios_ordenados = sorted(
        proprietarios,
        key=lambda p: (-p.percentual, p.cnpj or "", p.nome)
    )
    
    principal = proprietarios_ordenados[0]
    return formatar_nome_bruto(principal.nome, principal.cnpj)


def transformar_projeto(linha_csv: dict) -> dict:
    """
    Recebe um dict bruto do CSV e devolve um dict normalizado
    pronto para o Upsert. Exige as chaves obrigatórias.
    
    Atenção: `nome_bruto_principal_id` ainda não está aqui porque exige
    consulta ao banco. A função retorna a chave textual `nome_bruto_principal_str`.
    """
    ceg = str(linha_csv.get("CodCEG", "")).strip()
    if not ceg:
        raise ValueError("CEG ausente na linha.")

    ano = extrair_ano_iso(linha_csv.get("DatInicioVigencia", ""))
    uf = str(linha_csv.get("SigUFPrincipal", "")).strip()
    
    # Tratamento de municípios (lista) usando a coluna com o typo da ANEEL
    mun_bruto = str(linha_csv.get("DscMuninicpios", "")).strip()
    municipios = [m.strip() for m in mun_bruto.split(",")] if mun_bruto else []

    potencia = parse_float(linha_csv.get("MdaPotenciaOutorgadaKw"))
    if not uf or not municipios or potencia is None:
        raise ValueError(f"Campos obrigatórios ausentes no CEG {ceg} (UF, Município ou Potência).")

    sigla_origem = str(linha_csv.get("SigTipoGeracao", "")).strip()
    origem = MAPA_ORIGEM.get(sigla_origem)
    if not origem:
        raise ValueError(f"Origem desconhecida ou ausente no CEG {ceg}: {sigla_origem}")

    fase = str(linha_csv.get("DscFaseUsina", "")).strip()
    nome_bruto_str = extrair_dono_principal(linha_csv.get("DscPropriRegimePariticipacao", ""))

    lat = parse_float(linha_csv.get("NumCoordNEmpreendimento"))
    lon = parse_float(linha_csv.get("NumCoordEEmpreendimento"))

    # Coordenadas 0,0 viram NULL
    if lat == 0.0 and lon == 0.0:
        lat = None
        lon = None

    return {
        "ceg": ceg,
        "nome_projeto": str(linha_csv.get("NomEmpreendimento", "")).strip() or None,
        "uf": uf,
        "municipios": municipios,
        "origem": origem,
        "fase": fase,
        "potencia_outorgada_kw": potencia,
        "inicio_vigencia_ano": ano,
        "latitude": lat,
        "longitude": lon,
        "nome_bruto_principal_str": nome_bruto_str  # Chave temporária para a Etapa 5
    }