"""
Configuração de infraestrutura: dependências obrigatórias do processo
(banco de dados). Ausência aqui derruba o boot — falha rápido, na
importação do módulo.

NÃO importar este módulo em código que não depende de infraestrutura
(ex: lógica pura como matching/similaridade.py). Foi exatamente esse
acoplamento que fez testes de fuzz matching exigirem DATABASE_URL/Docker
pra rodar, sem nenhum motivo real.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _obter_database_url() -> str:
    valor = os.getenv("DATABASE_URL")
    if not valor:
        raise RuntimeError(
            "DATABASE_URL nao definida. Confira se o .env existe (copiado do "
            ".env.example) e se load_dotenv() esta encontrando o arquivo a "
            "partir do diretorio de onde o processo foi iniciado."
        )
    return valor


class InfraSettings:
    DATABASE_URL: str = _obter_database_url()


infra_settings = InfraSettings()