import enum

class EtlRunStatus(str, enum.Enum):
    sucesso = "sucesso"
    erro = "erro"
    em_andamento = "em_andamento"