import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { EChartsOption } from 'echarts';

import geoJsonData from '@/assets/brasil-uf.json';

// Dicionário para traduzir o código 'codarea' do IBGE para a sigla do Estado
const mapaSiglasUF: Record<string, string> = {
  '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
  '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA',
  '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP',
  '41': 'PR', '42': 'SC', '43': 'RS',
  '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'
};

export interface MapaGeoProps {
  customOptions?: EChartsOption;
  className?: string;
  loadingText?: string;
}

export function MapaGeo({
  customOptions,
  className = '',
  loadingText = 'Carregando mapa...'
}: MapaGeoProps) {
  const [isMapLoaded, setIsMapLoaded] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      echarts.registerMap('brasil', geoJsonData as any);
      setIsMapLoaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido ao registrar mapa');
    }
  }, []);

  const defaultOption: EChartsOption = {
    tooltip: {
      trigger: 'item',
      showDelay: 0,
      transitionDuration: 0.2,
      // Formata o tooltip para exibir bonito: "Estado: SP"
      formatter: (params: any) => {
        return params.name ? `<span style="font-weight:bold;">Estado: ${params.name}</span>` : '';
      }
    },
    series: [
      {
        name: 'Mapa do Brasil',
        type: 'map',
        map: 'brasil',
        // AS DUAS LINHAS MÁGICAS:
        nameProperty: 'codarea', // Diz ao ECharts para usar o código do IBGE para separar as regiões
        nameMap: mapaSiglasUF,   // Traduz o código numérico (ex: 35) para o nome (ex: SP)
        roam: true,
        zoom: 1.2,

        aspectScale: 0.95, // Força o mapa a ser mais largo. Quanto mais perto de 1 (ou maior), mais esticado horizontalmente ele fica.

        itemStyle: {
          areaColor: '#e2e8f0', 
          borderColor: '#ffffff',
          borderWidth: 1,
        },
        emphasis: {
          itemStyle: {
            areaColor: '#3b82f6', 
          },
          label: {
            show: true,
            color: '#ffffff',
            fontWeight: 'bold'
          }
        },
      }
    ]
  };

  const finalOption: EChartsOption = customOptions 
    ? { ...defaultOption, ...customOptions }
    : defaultOption;

  if (error) {
    return (
      <div className={`w-full h-full min-h-400px flex items-center justify-center bg-red-50 text-red-500 rounded-md border border-red-200 ${className}`}>
        <p className="font-medium text-sm">{error}</p>
      </div>
    );
  }

  if (!isMapLoaded) {
    return (
      <div className={`w-full h-full min-h-400px flex items-center justify-center bg-slate-50 text-slate-500 animate-pulse rounded-md ${className}`}>
        <p className="font-medium text-sm">{loadingText}</p>
      </div>
    );
  }

  return (
    <div className={`w-full h-full min-h-400px relative ${className}`}>
      <ReactECharts
        option={finalOption}
        style={{ height: '100%', width: '100%' }}
        className="react_for_echarts"
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
}