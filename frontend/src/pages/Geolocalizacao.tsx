import { MapaGeo } from '../components/geolocalizacao/MapaGeo';

export function PaginaGeolocalizacao() {
  return (
    <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200 mt-4">
      <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Geolocalização</h2>
          <span className="text-sm text-slate-500">Distribuição espacial do portfólio de geração de energia.</span>
        </div>
        
        <div className="mt-4 sm:mt-0 flex gap-2">
          {/* Aqui entrarão os controles para filtrar os dados do TanStack Query */}
        </div>
      </div>
      
      {/* CORREÇÃO: Removido o h-600px do className e adicionado o style nativo */}
      <div 
        className="w-full relative rounded-md overflow-hidden bg-slate-50 border border-slate-100"
        style={{ height: '600px', minHeight: '600px' }}
      >
        <MapaGeo />
      </div>
    </div>
  );
}