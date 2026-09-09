"""
Configuração de regras de negócio: valores com default sensato, sem
dependência de infraestrutura. Deve ser seguro importar isto em testes
de lógica pura sem precisar de banco, Docker ou .env configurado.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class RegrasNegocioSettings:
    LIMIAR_SIMILARIDADE_NOMES: float = float(
        os.getenv("LIMIAR_SIMILARIDADE_NOMES", "85.0")
    )


regras_negocio_settings = RegrasNegocioSettings()