"""
Cálculo de similaridade entre nomes normalizados usando RapidFuzz.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from rapidfuzz import fuzz, process
from rapidfuzz.utils import default_process

from backend.app.core.config_negocio import regras_negocio_settings


def calcular_pontuacao(nome_a: str, nome_b: str) -> float:
    """
    (sem mudança — continua correta e testada)
    """
    if not nome_a or not nome_b:
        raise ValueError("nome_a e nome_b não podem ser vazios")

    return fuzz.token_sort_ratio(nome_a, nome_b, processor=default_process)


@dataclass(frozen=True)
class Correspondencia:
    nome_origem: str
    nome_candidato: str
    pontuacao: float


def _preparar_para_comparacao(nome: str) -> str:
    """
    Reproduz manualmente o que fuzz.token_sort_ratio faz internamente:
    normaliza e ordena os tokens. Feito UMA VEZ por nome (não por par),
    e alimentado depois em fuzz.ratio via cdist — que tem implementação
    SIMD acelerada no RapidFuzz. token_sort_ratio não tem essa aceleração
    em cdist (não consta na lista de scorers com SIMD na documentação do
    projeto), e foi essa a causa raiz da lentidão medida (74.8s p/ 10k).
    """
    return " ".join(sorted(default_process(nome).split()))


def encontrar_correspondencias(
    nomes: Iterable[str],
    limiar: float | None = None,
) -> list[Correspondencia]:
    """
    Compara todos os nomes entre si (batch) via process.cdist com
    fuzz.ratio sobre tokens pré-ordenados — equivalente a
    token_sort_ratio, mas usando o caminho acelerado (SIMD) do cdist.
    """
    limiar = (
        limiar
        if limiar is not None
        else regras_negocio_settings.LIMIAR_SIMILARIDADE_NOMES
    )
    lista = list(nomes)
    n = len(lista)
    if n < 2:
        return []

    preparados = [_preparar_para_comparacao(nome) for nome in lista]

    matriz = process.cdist(
        preparados,
        preparados,
        scorer=fuzz.ratio,
        score_cutoff=limiar,
        workers=-1,
        dtype=np.float32,
    )

    linhas, colunas = np.triu_indices(n, k=1)
    pontuacoes = matriz[linhas, colunas]
    mascara = pontuacoes >= limiar

    return [
        Correspondencia(lista[i], lista[j], float(score))
        for i, j, score in zip(linhas[mascara], colunas[mascara], pontuacoes[mascara])
    ]