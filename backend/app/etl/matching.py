import logging
from rapidfuzz import process, fuzz
from rapidfuzz import utils as rapidfuzz_utils

logger = logging.getLogger(__name__)

def calcular_similaridade(nomes_brutos: list, clientes_base: list, threshold: float = 85.0) -> list[dict]:
    """
    Compara uma lista de nomes brutos contra a base de clientes oficiais.
    Retorna uma lista de dicionários prontos para o bulk insert.
    """
    logger.info(f"Iniciando matching: {len(nomes_brutos)} nomes brutos contra {len(clientes_base)} clientes.")
    
    # Prepara o dicionário de busca para o RapidFuzz.
    # O formato precisa ser {id_do_cliente: "NOME OFICIAL"}
    dict_clientes = {str(cliente.id): cliente.nome_oficial for cliente in clientes_base}
    
    sugestoes = []

    for raw in nomes_brutos:
        # extractOne retorna uma tupla: (string_encontrada, score, chave_do_dicionario)
        # Ex: ("EMPRESA X LTDA", 95.5, "uuid-do-cliente")
        match = process.extractOne(
            raw.nome_bruto,
            dict_clientes,
            scorer=fuzz.WRatio,
            processor=rapidfuzz_utils.default_process,
        )

        # Se encontrou algum match e o score for maior ou igual ao threshold de corte
        if match:
            string_encontrada, score, cliente_id = match
            
            if score >= threshold:
                sugestoes.append({
                    "nome_bruto_id": raw.id,
                    "cliente_sugerido_id": cliente_id,
                    "score_similaridade": round(score, 2)
                })

    logger.info(f"Matching finalizado. {len(sugestoes)} correspondências encontradas acima de {threshold}%.")
    return sugestoes