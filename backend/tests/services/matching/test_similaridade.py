import pytest

from backend.app.services.matching.similaridade import (
    calcular_pontuacao,
    encontrar_correspondencias,
)


class TestCalcularPontuacao:
    def test_nomes_identicos_pontuam_100(self):
        assert calcular_pontuacao("SOLAR SUL ENERGIA", "SOLAR SUL ENERGIA") == 100.0

    def test_ordem_de_palavras_diferente_ainda_pontua_alto(self):
        # token_sort_ratio deve ignorar ordem
        score = calcular_pontuacao("ENERGIA SOLAR SUL", "SOLAR SUL ENERGIA")
        assert score == 100.0

    def test_nomes_claramente_diferentes_pontuam_baixo(self):
        score = calcular_pontuacao("AMBIPAR ENERGIA", "VOLTALIA BRASIL")
        assert score < 50.0

    def test_variacao_pequena_pontua_alto_mas_nao_100(self):
        score = calcular_pontuacao("AMBIPAR SOL 01", "AMBIPAR SOL 02")
        assert 85.0 <= score < 100.0

    def test_nomes_vazios_levantam_erro(self):
        with pytest.raises(ValueError):
            calcular_pontuacao("", "ALGO")

    def test_termos_genericos_do_setor_geram_falso_positivo_conhecido(self):
        # Este teste documenta o risco, não valida um "certo": duas empresas
        # SEM relação nenhuma, mas com vocabulário do setor em comum, podem
        # pontuar acima do limiar. Serve de alerta se o limiar for baixado.
        score = calcular_pontuacao(
            "CENTRAL GERADORA SOLAR NORTE", "CENTRAL GERADORA SOLAR LESTE"
        )
        assert score > 70.0  # comprova o risco, não é o comportamento desejado


class TestEncontrarCorrespondencias:
    def test_retorna_apenas_pares_acima_do_limiar(self):
        nomes = ["AMBIPAR SOL 01", "AMBIPAR SOL 02", "VOLTALIA BRASIL"]
        resultado = encontrar_correspondencias(nomes, limiar=85.0)

        assert len(resultado) == 1
        assert resultado[0].nome_origem == "AMBIPAR SOL 01"
        assert resultado[0].nome_candidato == "AMBIPAR SOL 02"
        assert resultado[0].pontuacao >= 85.0

    def test_lista_vazia_nao_quebra(self):
        assert encontrar_correspondencias([]) == []

    def test_limiar_alto_filtra_tudo(self):
        nomes = ["AMBIPAR SOL 01", "AMBIPAR SOL 02"]
        resultado = encontrar_correspondencias(nomes, limiar=99.9)
        assert resultado == []