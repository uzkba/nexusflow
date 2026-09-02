"""

RISCO CONHECIDO, NÃO RESOLVIDO AQUI: `ceg` é PK (text) em `projetos_geracao`, mas o CSV
bruto tem linhas duplicadas por CEG (mesmo empreendimento com DscTipoOutorga diferente
— confirmado em amostra real). O upsert `ON CONFLICT DO UPDATE` citado no README vai
processar as duas linhas e a que rodar por último silenciosamente vence, sem log de
qual DscTipoOutorga foi descartado. Isso é decisão de Transform (Fase 2), não deste
módulo — mas fica registrado aqui porque é aqui que o dado duplicado é visto pela
primeira vez no pipeline.

DscMuninicpios: nome tem um typo propositalmente preservado — é assim que a ANEEL
nomeia a coluna, não um erro seu.
"""

from __future__ import annotations

from dataclasses import dataclass

EXPECTED_COLUMNS: list[str] = [
    "DatGeracaoConjuntoDados",
    "NomEmpreendimento",
    "IdeNucleoCEG",
    "CodCEG",
    "SigUFPrincipal",
    "SigTipoGeracao",
    "DscFaseUsina",
    "DscOrigemCombustivel",
    "DscFonteCombustivel",
    "DscTipoOutorga",
    "NomFonteCombustivel",
    "DatEntradaOperacao",
    "MdaPotenciaOutorgadaKw",
    "MdaPotenciaFiscalizadaKw",
    "MdaGarantiaFisicaKw",
    "IdcGeracaoQualificada",
    "NumCoordNEmpreendimento",
    "NumCoordEEmpreendimento",
    "DatInicioVigencia",
    "DatFimVigencia",
    "DscPropriRegimePariticipacao",
    "DscSubBacia",
    "DscMuninicpios",
]

# Colunas que o pipeline efetivamente usa a jusante — mapeadas 1:1 contra as colunas
# REAIS de `projetos_geracao` (README, seção "Modelagem de dados"). Se uma dessas
# faltar, é erro fatal — o registro não pode ser persistido sem ela. As demais são
# "nice to have"; a ausência delas gera warning, não aborta o pipeline.
#
# CORREÇÃO (2026-08-31): a lista anterior tinha sido montada só com a intuição de
# "o que parece importante", sem checar contra o schema real. Comparando agora com
# `projetos_geracao` no README, faltavam 3 colunas que alimentam campos de
# primeira classe da tabela: NomEmpreendimento (nome_projeto), as duas coordenadas
# (usadas na aba inteira de Geolocalização) e DatInicioVigencia (inicio_vigencia_ano,
# que é INDEXADO — filtro de ano no dashboard depende disso).
CRITICAL_COLUMNS: list[str] = [
    "CodCEG",                    
    "NomEmpreendimento",       
    "SigUFPrincipal",            
    "DscMuninicpios",           
    "DscOrigemCombustivel",     
    "DscFaseUsina",            
    "MdaPotenciaOutorgadaKw",   
    "DatInicioVigencia",       
    "NumCoordNEmpreendimento",  
    "NumCoordEEmpreendimento",   
]


CLIENT_COLUMN_LABELS: dict[str, str] = {
    "CodCEG": "CEG",
    "NomEmpreendimento": "Empreendimento",
    "SigUFPrincipal": "UF",
    "SigTipoGeracao": "Fonte",
    "DscFaseUsina": "Fase",
    "DscOrigemCombustivel": "Origem",
    "DscFonteCombustivel": "Tipo",
    "DscTipoOutorga": "Tipo de Atuação",
    "NomFonteCombustivel": "Combustível Final",
    "DatEntradaOperacao": "Entrada em Operação",
    "MdaPotenciaOutorgadaKw": "Potência Outorgada (kW)",
    "MdaPotenciaFiscalizadaKw": "Potência Fiscalizada (kW)",
    "MdaGarantiaFisicaKw": "Garantia Física (kW)",
    "IdcGeracaoQualificada": "Geração Qualificada",
    "NumCoordNEmpreendimento": "Latitude Decimal",
    "NumCoordEEmpreendimento": "Longitude Decimal",
    "DatInicioVigencia": "Início Vigência",
    "DatFimVigencia": "Fim Vigência",
    "DscPropriRegimePariticipacao": "Proprietário / CNPJ / Regime de Exploração",
    "DscSubBacia": "Sub-Bacia",
    "DscMuninicpios": "Município (s)",
}


KNOWN_FASE_VALUES: set[str] = {"Operação", "Construção", "Construção não iniciada"}
KNOWN_ORIGEM_VALUES: set[str] = {"Solar", "Hídrica", "Fóssil", "Biomassa", "Eólica", "Nuclear"}


ORIGEM_EM_ESCOPO: set[str] = {"Solar", "Eólica"}
FASE_EM_ESCOPO: set[str] = {"Construção não iniciada"}


@dataclass
class UnknownValuesResult:
    fase_desconhecidas: list[str]
    origem_desconhecidas: list[str]

    @property
    def tem_valores_novos(self) -> bool:
        return bool(self.fase_desconhecidas or self.origem_desconhecidas)

    def as_dict(self) -> dict:
        return {
            "fase_desconhecidas": self.fase_desconhecidas,
            "origem_desconhecidas": self.origem_desconhecidas,
        }


def check_unknown_fase_origem_values(fase_series, origem_series) -> UnknownValuesResult:

    fase_vistas = set(fase_series.dropna().unique())
    origem_vistas = set(origem_series.dropna().unique())

    return UnknownValuesResult(
        fase_desconhecidas=sorted(fase_vistas - KNOWN_FASE_VALUES),
        origem_desconhecidas=sorted(origem_vistas - KNOWN_ORIGEM_VALUES),
    )


@dataclass
class ColumnValidationResult:
    ok: bool
    missing_critical: list[str]
    missing_optional: list[str]
    unexpected_new: list[str]

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "missing_critical": self.missing_critical,
            "missing_optional": self.missing_optional,
            "unexpected_new": self.unexpected_new,
        }


def validate_columns(actual_columns: list[str]) -> ColumnValidationResult:
    actual_set = set(actual_columns)
    expected_set = set(EXPECTED_COLUMNS)
    critical_set = set(CRITICAL_COLUMNS)

    missing = expected_set - actual_set
    missing_critical = sorted(missing & critical_set)
    missing_optional = sorted(missing - critical_set)
    unexpected_new = sorted(actual_set - expected_set)

    return ColumnValidationResult(
        ok=len(missing_critical) == 0,
        missing_critical=missing_critical,
        missing_optional=missing_optional,
        unexpected_new=unexpected_new,
    )