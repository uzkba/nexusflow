import asyncio
import csv

from sqlalchemy import select

from backend.app.db.session import AsyncSessionLocal
from backend.app.model.models import RawName
from backend.app.services.matching.normalizacao import normalizar_nome_razao_social
from backend.app.services.matching.similaridade import encontrar_correspondencias


async def main() -> None:
    async with AsyncSessionLocal() as session:
        resultado = await session.execute(select(RawName.nome_bruto))
        nomes_brutos = resultado.scalars().all()

    print(f"Total de nomes_brutos no banco: {len(nomes_brutos)}")

    normalizados = []
    falhas = []
    for nome in nomes_brutos:
        try:
            normalizados.append(normalizar_nome_razao_social(nome))
        except ValueError as erro:
            falhas.append((nome, str(erro)))

    if falhas:
        print(f"\n{len(falhas)} nomes rejeitados pela normalização (fora da comparação):")
        for nome, erro in falhas[:10]:
            print(f"  - {nome!r}: {erro}")
        if len(falhas) > 10:
            print(f"  ... e mais {len(falhas) - 10}")

    print(f"\nComparando {len(normalizados)} nomes normalizados, limiar=85.0...")
    correspondencias = encontrar_correspondencias(normalizados, limiar=85.0)
    print(f"{len(correspondencias)} pares encontrados acima do limiar.\n")

    caminho_saida = "backend/data/validacao_limiar_similaridade.csv"
    with open(caminho_saida, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["nome_origem", "nome_candidato", "pontuacao"])
        for c in sorted(correspondencias, key=lambda x: x.pontuacao):
            escritor.writerow([c.nome_origem, c.nome_candidato, f"{c.pontuacao:.1f}"])

    print(f"Resultado salvo em {caminho_saida}")
    print("Abra o CSV ordenado por pontuação crescente — revise primeiro os pares")
    print("mais próximos do limiar (85-90%), é onde falso positivo/negativo aparece.")


if __name__ == "__main__":
    asyncio.run(main())