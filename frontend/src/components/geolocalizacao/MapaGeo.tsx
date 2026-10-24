// frontend/src/components/geolocalizacao/MapaGeo.tsx
import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { GeolocalizacaoItem } from '../../hooks/use-geolocalizacao';
// Assume-se que o JSON já está importado e o mapa registrado
import brasilUfJson from '../../assets/brasil-uf.json';

// Registo do mapa (se já não estiver a ser feito na inicialização da app)
echarts.registerMap('brasil', brasilUfJson as any);

interface MapaGeoProps {
  dados: GeolocalizacaoItem[];
}

export const MapaGeo: React.FC<MapaGeoProps> = ({ dados }) => {
  // Transformar os dados agregados em pontos (Scatters) baseados nos municípios
  const scatterData = useMemo(() => {
    return dados.map((item) => {
      return {
        name: `${item.municipio} (${item.uf})`,
        // ECharts exige [longitude, latitude]. 
        // Adiciona estes campos à tua query/schema no backend para os pontos não ficarem em [0,0]
        value: [(item as any).longitude || 0, (item as any).latitude || 0],
        municipio: item.municipio,
        quantidade_projetos: item.quantidade_projetos,
        potencia_total: item.potencia_total
      };
    });
  }, [dados]);

  const options = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        // Tooltip para os pontos agregados por município
        if (params.seriesType === 'effectScatter') {
          return `
            <div style="font-family: sans-serif; font-size: 13px;">
              <strong>${params.data.municipio}</strong><br/>
              Projetos: ${params.data.quantidade_projetos}<br/>
              Potência: ${params.data.potencia_total} kW
            </div>
          `;
        }
        // Tooltip fallback para as regiões (UF) do mapa base
        return params.name; 
      }
    },
    geo: {
      map: 'brasil',
      roam: true, // Permite zoom e drag
      aspectScale: 0.95,
      itemStyle: {
        areaColor: '#e2e8f0', // tailwind slate-200
        borderColor: '#94a3b8', // tailwind slate-400
      },
      emphasis: {
        itemStyle: {
          areaColor: '#cbd5e1'
        }
      }
    },
    series: [
      {
        name: 'Projetos',
        type: 'effectScatter',
        coordinateSystem: 'geo',
        data: scatterData,
        symbolSize: 8,
        itemStyle: {
          color: '#2563eb', // tailwind blue-600
          shadowBlur: 10,
          shadowColor: '#2563eb'
        },
        large: true 
      }
    ]
  };

  return (
    <ReactECharts
      option={options}
      style={{ height: '600px', width: '100%' }}
      opts={{ renderer: 'canvas' }}
      notMerge={true}
    />
  );
};