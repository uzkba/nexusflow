import React from 'react';
import { DiffItem } from '../types/pendencias';

interface DiffViewerProps {
  diffs: Record<string, DiffItem>;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ diffs }) => {
  // Verifica se o objeto existe e tem chaves
  if (!diffs || Object.keys(diffs).length === 0) return null;

  return (
    <div className="w-full border rounded-md overflow-hidden text-sm">
      <div className="bg-gray-100 font-medium grid grid-cols-3 p-2 border-b">
        <div>Campo Modificado</div>
        <div>Valor Atual</div>
        <div>Novo Valor Sugerido</div>
      </div>
      <div className="divide-y">
        {Object.entries(diffs).map(([campo, diff]) => (
          <div key={campo} className="grid grid-cols-3 p-2 items-center gap-4">
            <span className="font-semibold text-gray-700">{campo}</span>
            <span className="text-red-600 bg-red-50 p-1.5 rounded line-through truncate">
              {diff.valor_antigo ?? 'N/A'}
            </span>
            <span className="text-green-700 bg-green-50 p-1.5 rounded truncate font-medium">
              {diff.valor_novo ?? 'N/A'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};