import ReactECharts from "echarts-for-react";
import type { RankingCliente } from "../../types/dashboard";

export function GraficoRanking({ dados }: { dados: RankingCliente[] }) {
  if (!dados || dados.length === 0) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">Sem dados para exibir</div>;
  }

  // O ECharts desenha barras horizontais de baixo para cima. 
  // Invertemos o array para o Top 1 ficar no topo do gráfico.
  const dadosInvertidos = [...dados].reverse();

  const options = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      valueFormatter: (value: number) => `${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} MW`
    },
    grid: {
      top: "10%",
      left: "2%",
      right: "12%", // Dá mais espaço à direita para não cortar a palavra "MW"
      bottom: "5%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
      name: "MW",
      nameLocation: "end",
    },
    yAxis: {
      type: "category",
      data: dadosInvertidos.map((d) => 
        d.nome_oficial.length > 25 ? d.nome_oficial.substring(0, 25) + "..." : d.nome_oficial
      ),
      axisLabel: {
        fontSize: 12,
        interval: 0, // Força a exibição de todas as linhas de forma separada
      }
    },
    series: [
      {
        name: "Potência Total",
        type: "bar",
        barWidth: "50%", // Define a espessura da barra para dar espaçamento entre elas
        itemStyle: { color: "#6366f1", borderRadius: [0, 4, 4, 0] },
        barMinHeight: 5, // Garante que a barra apareça mesmo que o valor seja muito pequeno
        label: {
          show: true,
          position: "right",
          formatter: (params: any) => Number(params.value).toLocaleString("pt-BR", { maximumFractionDigits: 0 })
        },
        data: dadosInvertidos.map((d) => Number(d.potencia_total_mw)),
      },
    ],
  };

  // Define uma altura fixa (350px) para que o gráfico não fique esmagado
  return <ReactECharts option={options} style={{ height: "350px", width: "100%" }} opts={{ renderer: "svg" }} />;
}