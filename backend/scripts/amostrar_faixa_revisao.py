import csv
import random

with open("backend/data/validacao_limiar_similaridade.csv", encoding="utf-8") as arquivo:
    leitor = csv.DictReader(arquivo)
    faixa_85_90 = [
        linha for linha in leitor if 85 <= float(linha["pontuacao"]) < 90
    ]

amostra = random.sample(faixa_85_90, min(35, len(faixa_85_90)))
amostra.sort(key=lambda linha: float(linha["pontuacao"]))

for linha in amostra:
    print(f"{linha['pontuacao']}  |  {linha['nome_origem']}  <->  {linha['nome_candidato']}")