
import re
import unicodedata


class CnpjInvalidoError(Exception):

    def __init__(self, codigo: str, valor_original: str, mensagem: str):
        self.codigo = codigo
        self.valor_original = valor_original
        self.mensagem = mensagem
        super().__init__(f"[{codigo}] {mensagem}")



_CNPJ_CARACTERE_INVALIDO = re.compile(r"[^0-9A-Z]")


_PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS_DV2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def _valor_para_dv(caractere: str) -> int:
    return ord(caractere) - 48


def _calcular_digito_verificador(valores: list[int], pesos: list[int]) -> int:
    soma = sum(v * p for v, p in zip(valores, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def limpar_cnpj(cnpj_bruto: str, *, validar_digito_verificador: bool = True) -> str:
    if cnpj_bruto is None or not cnpj_bruto.strip():
        raise CnpjInvalidoError("VAZIO", cnpj_bruto, "CNPJ vazio ou não informado.")

    limpo = _CNPJ_CARACTERE_INVALIDO.sub("", cnpj_bruto.upper())

    if len(limpo) != 14:
        raise CnpjInvalidoError(
            "TAMANHO_INVALIDO",
            cnpj_bruto,
            f"CNPJ deve ter 14 caracteres após limpeza, encontrado {len(limpo)}.",
        )

    if not limpo[12:].isdigit():
        raise CnpjInvalidoError(
            "DV_NAO_NUMERICO",
            cnpj_bruto,
            "Os dois últimos caracteres (dígitos verificadores) devem ser numéricos, mesmo "
            "no formato alfanumérico.",
        )

    if len(set(limpo)) == 1:
        raise CnpjInvalidoError(
            "SEQUENCIA_REPETIDA",
            cnpj_bruto,
            "CNPJ com todos os caracteres iguais não é válido (ex: 00000000000000).",
        )

    if validar_digito_verificador:
        valores_base = [_valor_para_dv(c) for c in limpo[:12]]
        dv1 = _calcular_digito_verificador(valores_base, _PESOS_DV1)
        dv2 = _calcular_digito_verificador(valores_base + [dv1], _PESOS_DV2)
        if int(limpo[12]) != dv1 or int(limpo[13]) != dv2:
            raise CnpjInvalidoError(
                "DIGITO_VERIFICADOR_INVALIDO",
                cnpj_bruto,
                "Dígitos verificadores não conferem pelo cálculo Módulo 11.",
            )

    return limpo


_PADRAO_NAO_LETRA = re.compile(r"[^A-Z\s]")


_PADRAO_SUFIXO_SOCIETARIO = re.compile(
    r"\b(S\s*A|LTDA|EIRELI|EPP|SPE|MEI|ME)\b\s*$"
)

_PADRAO_ESPACOS_MULTIPLOS = re.compile(r"\s+")


class NomeInvalidoError(Exception):
    def __init__(self, codigo: str, valor_original: str, mensagem: str):
        self.codigo = codigo
        self.valor_original = valor_original
        self.mensagem = mensagem
        super().__init__(f"[{codigo}] {mensagem}")


def normalizar_nome_razao_social(nome_bruto: str) -> str:
    if nome_bruto is None or not nome_bruto.strip():
        raise NomeInvalidoError("VAZIO", nome_bruto, "Nome/Razão Social vazio ou não informado.")

    nome = nome_bruto.upper()

    nome = unicodedata.normalize("NFKD", nome)
    nome = "".join(caractere for caractere in nome if not unicodedata.combining(caractere))

    nome = _PADRAO_NAO_LETRA.sub(" ", nome)

    while True:
        nome_sem_sufixo = _PADRAO_SUFIXO_SOCIETARIO.sub("", nome).strip()
        if nome_sem_sufixo == nome.strip():
            nome = nome_sem_sufixo
            break
        nome = nome_sem_sufixo

    nome = _PADRAO_ESPACOS_MULTIPLOS.sub(" ", nome).strip()

    if not nome:
        raise NomeInvalidoError(
            "RESULTADO_VAZIO_APOS_NORMALIZACAO",
            nome_bruto,
            "Nome não contém nenhuma letra após remover pontuação/sufixo societário.",
        )

    return nome