import csv
from collections import Counter

faixas = Counter()

with open("backend/data/validacao_limiar_similaridade.csv", encoding="utf-8") as arquivo:
    leitor = csv.DictReader(arquivo)
    for linha in leitor:
        score = float(linha["pontuacao"])
        if score < 90:
            faixas["85-90 (revisar com atenção)"] += 1
        elif score < 95:
            faixas["90-95"] += 1
        else:
            faixas["95-100 (provavelmente óbvio)"] += 1

for faixa, contagem in faixas.items():
    print(f"{faixa}: {contagem}")