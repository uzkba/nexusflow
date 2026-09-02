"""
Testes unitários para app.services.matching.normalizacao.

Cobre os cenários de borda exigidos pelo critério de aceite:
    - CNPJ: só números OU alfanumérico (formato vigente desde 31/07/2026), rejeição
      estruturada de inválidos.
    - Nome/Razão Social: "EMPRESA EXEMPLO SA" e "Empresa Exemplo S/A" -> mesma base;
      nome vazio é rejeitado, não silenciosamente aceito.
"""

import pytest

from backend.app.services.matching.normalizacao import (
    CnpjInvalidoError,
    NomeInvalidoError,
    limpar_cnpj,
    normalizar_nome_razao_social,
)


def _dv(valores, pesos):
    resto = sum(v * p for v, p in zip(valores, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def _cnpj_alfanumerico_valido(base12: str) -> str:
    """Monta um CNPJ alfanumérico de 14 chars com DVs corretos a partir das 12 primeiras
    posições, usando o mesmo algoritmo (ASCII-48 + Módulo 11) implementado em produção —
    útil só para gerar massa de teste válida, não é o código sob teste."""
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    valores = [ord(c) - 48 for c in base12]
    d1 = _dv(valores, pesos1)
    d2 = _dv(valores + [d1], pesos2)
    return f"{base12}{d1}{d2}"


# ---------------------------------------------------------------------------
# limpar_cnpj
# ---------------------------------------------------------------------------

class TestLimparCnpj:

    # CNPJ numérico de testes, amplamente usado como exemplo válido (dígitos verificadores
    # conferem pelo Módulo 11: DV1=8, DV2=1).
    CNPJ_NUMERICO_VALIDO = "11222333000181"

    @pytest.mark.parametrize(
        "cnpj_bruto",
        [
            "11222333000181",
            "11.222.333/0001-81",
            " 11.222.333/0001-81 ",
            "11 222 333 0001 81",
            "11-222-333-0001-81",
        ],
    )
    def test_aceita_variacoes_de_mascara_cnpj_numerico(self, cnpj_bruto):
        resultado = limpar_cnpj(cnpj_bruto)
        assert resultado == self.CNPJ_NUMERICO_VALIDO
        assert len(resultado) == 14

    def test_rejeita_none(self):
        with pytest.raises(CnpjInvalidoError) as exc:
            limpar_cnpj(None)
        assert exc.value.codigo == "VAZIO"

    def test_rejeita_string_vazia(self):
        with pytest.raises(CnpjInvalidoError) as exc:
            limpar_cnpj("")
        assert exc.value.codigo == "VAZIO"

    def test_rejeita_string_so_espacos(self):
        with pytest.raises(CnpjInvalidoError) as exc:
            limpar_cnpj("   ")
        assert exc.value.codigo == "VAZIO"

    @pytest.mark.parametrize(
        "cnpj_bruto",
        [
            "1122233300018",     # 13 caracteres
            "112223330001811",   # 15 caracteres
            "123",                # muito curto
        ],
    )
    def test_rejeita_tamanho_invalido(self, cnpj_bruto):
        with pytest.raises(CnpjInvalidoError) as exc:
            limpar_cnpj(cnpj_bruto)
        assert exc.value.codigo == "TAMANHO_INVALIDO"

    @pytest.mark.parametrize(
        "cnpj_bruto",
        ["00000000000000", "11111111111111", "99999999999999"],
    )
    def test_rejeita_sequencia_repetida(self, cnpj_bruto):
        # Nota: não há caso análogo com letra repetida (ex: "AAAAAAAAAAAAAA") — os dois
        # últimos caracteres (DV) precisam ser dígito numérico, então qualquer sequência
        # de letra repetida já cai em 'DV_NAO_NUMERICO' antes de chegar nesta checagem
        # (ver test_rejeita_dv_nao_numerico_com_tamanho_correto).
        with pytest.raises(CnpjInvalidoError) as exc:
            limpar_cnpj(cnpj_bruto)
        assert exc.value.codigo == "SEQUENCIA_REPETIDA"

    def test_rejeita_digito_verificador_invalido(self):
        # Mesmo prefixo do CNPJ válido, mas com DVs errados.
        with pytest.raises(CnpjInvalidoError) as exc:
            limpar_cnpj("11222333000199")
        assert exc.value.codigo == "DIGITO_VERIFICADOR_INVALIDO"

    def test_bypassa_validacao_de_dv_quando_desativado(self):
        # 14 caracteres válidos em tamanho e sem sequência repetida, mas DV incorreto —
        # só passa com validar_digito_verificador=False.
        resultado = limpar_cnpj("11222333000199", validar_digito_verificador=False)
        assert resultado == "11222333000199"

    def test_preserva_valor_original_no_erro_para_log(self):
        entrada = "11.222.333/0001-99"
        with pytest.raises(CnpjInvalidoError) as exc:
            limpar_cnpj(entrada)
        assert exc.value.valor_original == entrada

    # -- CNPJ alfanumérico (vigente desde 31/07/2026, IN RFB 2.229/2024) --

    def test_aceita_cnpj_alfanumerico_com_dv_valido(self):
        cnpj_valido = _cnpj_alfanumerico_valido("12ABC3450001")
        resultado = limpar_cnpj(cnpj_valido)
        assert resultado == cnpj_valido
        assert len(resultado) == 14

    def test_aceita_cnpj_alfanumerico_com_mascara(self):
        cnpj_valido = _cnpj_alfanumerico_valido("12ABC3450001")
        com_mascara = (
            f"{cnpj_valido[:2]}.{cnpj_valido[2:5]}.{cnpj_valido[5:8]}"
            f"/{cnpj_valido[8:12]}-{cnpj_valido[12:]}"
        )
        resultado = limpar_cnpj(com_mascara)
        assert resultado == cnpj_valido

    def test_normaliza_letra_minuscula_para_maiuscula(self):
        cnpj_valido = _cnpj_alfanumerico_valido("12ABC3450001")
        resultado = limpar_cnpj(cnpj_valido.lower())
        assert resultado == cnpj_valido

    def test_rejeita_alfanumerico_com_digito_verificador_invalido(self):
        with pytest.raises(CnpjInvalidoError) as exc:
            limpar_cnpj("12ABC345000199")
        assert exc.value.codigo == "DIGITO_VERIFICADOR_INVALIDO"

    def test_rejeita_dv_nao_numerico_com_tamanho_correto(self):
        # Letra numa das duas últimas posições (DV) é inválida mesmo no formato novo —
        # a RFB manteve os dois DVs como dígito numérico em ambos os formatos.
        # 12 posições base + 'A' + '1' = 14 caracteres, DV1 não numérico.
        with pytest.raises(CnpjInvalidoError) as exc:
            limpar_cnpj("12ABC3450001A1")
        assert exc.value.codigo == "DV_NAO_NUMERICO"


# ---------------------------------------------------------------------------
# normalizar_nome_razao_social
# ---------------------------------------------------------------------------

class TestNormalizarNomeRazaoSocial:

    def test_criterio_de_aceite_sa_com_e_sem_barra(self):
        # Critério de aceite explícito da task.
        assert (
            normalizar_nome_razao_social("EMPRESA EXEMPLO SA")
            == normalizar_nome_razao_social("Empresa Exemplo S/A")
            == "EMPRESA EXEMPLO"
        )

    @pytest.mark.parametrize(
        "sufixo_variante",
        ["LTDA", "Ltda", "ltda.", "LTDA.", " LTDA "],
    )
    def test_remove_sufixo_ltda_em_variacoes_de_caixa_e_pontuacao(self, sufixo_variante):
        resultado = normalizar_nome_razao_social(f"Empresa Exemplo {sufixo_variante}")
        assert resultado == "EMPRESA EXEMPLO"

    def test_remove_sufixos_encadeados_spe_ltda(self):
        # Comum no setor de geração de energia: "USINA X SPE LTDA".
        resultado = normalizar_nome_razao_social("Usina Solar Bonfim SPE LTDA")
        assert resultado == "USINA SOLAR BONFIM"

    def test_remove_acentuacao(self):
        resultado = normalizar_nome_razao_social("Geração de Energia São João LTDA")
        assert resultado == "GERACAO DE ENERGIA SAO JOAO"

    def test_colapsa_espacos_duplos_e_faz_trim(self):
        resultado = normalizar_nome_razao_social("  Empresa    Exemplo   ME  ")
        assert resultado == "EMPRESA EXEMPLO"

    def test_remove_caracteres_especiais_sem_colar_palavras(self):
        resultado = normalizar_nome_razao_social("Empresa-Exemplo & Cia. Ltda")
        assert resultado == "EMPRESA EXEMPLO CIA"

    def test_nao_remove_sufixo_de_dentro_de_outra_palavra(self):
        # "ME" dentro de "NOME" e "SA" dentro de "CASA" não podem ser removidos —
        # só quando o sufixo é um token isolado no fim da string.
        assert normalizar_nome_razao_social("Comercial Nome Proprio LTDA") == "COMERCIAL NOME PROPRIO"
        assert normalizar_nome_razao_social("Reforma de Casa LTDA") == "REFORMA DE CASA"

    def test_pessoa_fisica_sem_sufixo_nao_e_alterada_alem_do_padrao(self):
        # Caso real do dataset ANEEL: pessoa física sem CNPJ, sem sufixo societário.
        resultado = normalizar_nome_razao_social("José da Silva")
        assert resultado == "JOSE DA SILVA"

    def test_valor_literal_nao_informado_e_preservado(self):
        # Caso real do dataset ANEEL (ver nomes_brutos): "Não Informado" deve virar seu
        # próprio nome normalizado, não ser descartado.
        resultado = normalizar_nome_razao_social("Não Informado")
        assert resultado == "NAO INFORMADO"

    # -- Rejeição de nome vazio (decisão: não aceitar mais silenciosamente) --

    def test_rejeita_none(self):
        with pytest.raises(NomeInvalidoError) as exc:
            normalizar_nome_razao_social(None)
        assert exc.value.codigo == "VAZIO"

    def test_rejeita_string_vazia(self):
        with pytest.raises(NomeInvalidoError) as exc:
            normalizar_nome_razao_social("")
        assert exc.value.codigo == "VAZIO"

    def test_rejeita_string_so_espacos(self):
        with pytest.raises(NomeInvalidoError) as exc:
            normalizar_nome_razao_social("    ")
        assert exc.value.codigo == "VAZIO"

    def test_rejeita_entrada_que_so_tem_sufixo_societario(self):
        # "LTDA." não tem nenhum conteúdo além do sufixo/pontuação — vira vazio após
        # normalização e é rejeitado, não retornado como "".
        with pytest.raises(NomeInvalidoError) as exc:
            normalizar_nome_razao_social("LTDA.")
        assert exc.value.codigo == "RESULTADO_VAZIO_APOS_NORMALIZACAO"

    def test_rejeita_entrada_so_com_pontuacao(self):
        with pytest.raises(NomeInvalidoError) as exc:
            normalizar_nome_razao_social("-----")
        assert exc.value.codigo == "RESULTADO_VAZIO_APOS_NORMALIZACAO"

    def test_preserva_valor_original_no_erro_para_log(self):
        entrada = "LTDA."
        with pytest.raises(NomeInvalidoError) as exc:
            normalizar_nome_razao_social(entrada)
        assert exc.value.valor_original == entrada