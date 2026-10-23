"""
Garante que a constante do sentinela no app é igual ao valor literal gravado
na migration que o cria. Se alguém mudar um dos dois, este teste quebra.
"""

import importlib.util
from pathlib import Path

from backend.app.core.constantes import SENTINELA_CLIENTE_ID, SENTINELA_NOME

# backend/tests/test_constantes.py -> parents[2] é a raiz do repositório
RAIZ = Path(__file__).resolve().parents[2]
REVISAO_SENTINELA = "b7c1e94a3d52"


def _carregar_migration():
    arquivos = list((RAIZ / "alembic" / "versions").glob(f"{REVISAO_SENTINELA}_*.py"))
    assert len(arquivos) == 1, f"esperava 1 migration {REVISAO_SENTINELA}, achei {arquivos}"
    spec = importlib.util.spec_from_file_location("migration_sentinela", arquivos[0])
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_uuid_do_sentinela_igual_ao_da_migration():
    migration = _carregar_migration()
    assert str(SENTINELA_CLIENTE_ID) == migration.SENTINELA_CLIENTE_ID


def test_nome_do_sentinela_igual_ao_da_migration():
    migration = _carregar_migration()
    assert SENTINELA_NOME == migration.SENTINELA_NOME


def test_migration_encadeada_na_ponta_anterior():
    migration = _carregar_migration()
    assert migration.down_revision == "31f43aa71d80"