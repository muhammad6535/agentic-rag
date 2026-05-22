import type { SourceChunk } from '../types';

interface SourcePanelProps {
  sources: SourceChunk[];
}

export default function SourcePanel({ sources }: SourcePanelProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-6 border-t border-gray-200 pt-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Sources ({sources.length})
      </h3>
      <div className="space-y-3">
        {sources.map((source, idx) => (
          <div
            key={source.id}
            className="bg-gray-50 rounded-lg border border-gray-200 p-3 text-sm"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-indigo-600">
                [{idx + 1}] {source.document_name} — Chunk {source.chunk_index}
              </span>
              <span className="text-xs text-gray-400">
                Score: {(source.score * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-gray-600 text-xs leading-relaxed line-clamp-4">
              {source.content}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
