import enum

class GenerationSource(str, enum.Enum):
    solar = "Solar"
    eolica = "Eólica"

class PlantPhase(str, enum.Enum):
    construcao_nao_iniciada = "Construção não iniciada"

class ReviewStatus(str, enum.Enum):
    pendente = "pendente"
    aprovado = "aprovado"
    rejeitado = "rejeitado"