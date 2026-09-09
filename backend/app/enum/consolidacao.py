import enum

class ConsolidationStatus(str, enum.Enum):
    pendente = "pendente"
    aprovado = "aprovado"
    rejeitado = "rejeitado"

class MotivoPendenciaEnum(str, enum.Enum):
    consolidacao_nome = "consolidacao_nome"
    alteracao_dado = "alteracao_dado"