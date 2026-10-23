import ReactECharts from "echarts-for-react";
import type { OrigemGrafico } from "../../types/dashboard";

export function GraficoOrigem({ dados }: { dados: OrigemGrafico[] }) {
  if (!dados || dados.length === 0) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">Sem dados para exibir</div>;
  }

  const options = {
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} MW ({d}%)",
    },
    legend: {
      type: "scroll",
      orient: "vertical", // Coloca a legenda em pé (lista vertical)
      right: "5%",        // Encosta a legenda na direita
      top: "center",      // Centraliza a legenda verticalmente
      textStyle: { fontSize: 11 },
    },
    series: [
      {
        type: "pie",
        radius: ["55%", "85%"], // Aumenta bastante o tamanho da rosca
        center: ["40%", "50%"], // Desloca a rosca um pouco para a esquerda para dar espaço à legenda
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: "#fff",
          borderWidth: 2,
        },
        label: {
          show: false,
          position: "center",
        },
        labelLine: {
          show: false,
        },
        data: dados.map((d) => ({
          value: Number(d.potencia_total_mw).toFixed(2),
          name: d.origem,
        })),
      },
    ],
  };

  // Altura fixa aplicada aqui para o gráfico não ser esmagado
  return (
    <ReactECharts 
      option={options} 
      style={{ height: "350px", width: "100%" }} 
      opts={{ renderer: "svg" }} 
    />
  );
}