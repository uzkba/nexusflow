"""
Teste de performance para encontrar_correspondencias em volume alvo
(critério de aceite do Cartão 9: 10 mil registros cruzados sem gargalo
significativo).

Marcado como 'slow' — não roda por padrão, só quando pedido
explicitamente. Ver pytest.ini para o registro do marker.
"""
import time

import pytest

from backend.app.services.matching.similaridade import encontrar_correspondencias


def _gerar_nomes_sinteticos(quantidade: int) -> list[str]:
    """
    Gera nomes sintéticos que imitam o padrão real de nomes_brutos:
    mistura termos genéricos do setor (que geram similaridade real
    entre registros) com identificadores únicos, em vez de strings
    aleatórias sem relação nenhuma entre si — senão o teste mede
    performance de um cenário que não existe na prática.
    """
    termos_setor = ["CENTRAL GERADORA SOLAR", "USINA EOLICA", "COMPLEXO FOTOVOLTAICO"]
    return [
        f"{termos_setor[i % len(termos_setor)]} {i:05d}"
        for i in range(quantidade)
    ]


@pytest.mark.slow
def test_performance_10k_registros_nao_apresenta_gargalo():
    nomes = _gerar_nomes_sinteticos(10_000)

    inicio = time.perf_counter()
    resultado = encontrar_correspondencias(nomes, limiar=85.0)
    duracao = time.perf_counter() - inicio

    # TODO: threshold de tempo ainda não confirmado com quem definiu o
    # critério de aceite — 60s é um chute conservador, não um número
    # combinado. Ajustar quando isso for validado.
    assert duracao < 60.0, f"Levou {duracao:.1f}s — investigar gargalo"
    print(f"\nDuração real: {duracao:.2f}s")   # <- linha nova, só isso
    assert isinstance(resultado, list)