"""
Constantes de negócio compartilhadas entre ETL, serviços e testes.

Ficam aqui (e não em config_negocio.py) porque NÃO vêm de variável de
ambiente: são valores fixos do domínio.
"""

import uuid

# Cliente sentinela para obras cujo proprietário o SIGA não informa
# ("Não Informado"). O mesmo UUID está LITERAL na migration
# b7c1e94a3d52; backend/tests/test_constantes.py garante a igualdade.
SENTINELA_CLIENTE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SENTINELA_NOME = "Não Informado"