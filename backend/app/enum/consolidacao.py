import enum

class ConsolidationStatus(str, enum.Enum):
    pendente = "pendente"
    aprovado = "aprovado"
    rejeitado = "rejeitado"