import { useState, useEffect } from 'react';
import { listDocuments, getDocumentChunks } from '../services/api';
import type { Document, Chunk } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';

export default function AdminPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDocuments()
      .then((data) => setDocuments(data.documents))
      .catch(() => setError('Failed to load documents'))
      .finally(() => setLoading(false));
  }, []);

  const loadChunks = async (docId: string) => {
    setSelectedDoc(docId);
    setChunksLoading(true);
    try {
      const data = await getDocumentChunks(docId);
      setChunks(data.chunks);
    } catch {
      setError('Failed to load chunks');
    } finally {
      setChunksLoading(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading admin panel..." />;

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Admin / Debug</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Document list */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Documents ({documents.length})
            </h2>
            {documents.length === 0 ? (
              <p className="text-sm text-gray-500">No documents uploaded.</p>
            ) : (
              <div className="space-y-2">
                {documents.map((doc) => (
                  <button
                    key={doc.id}
                    onClick={() => loadChunks(doc.id)}
                    className={`w-full text-left p-3 rounded-lg text-sm transition-colors ${
                      selectedDoc === doc.id
                        ? 'bg-indigo-50 border border-indigo-200'
                        : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
                    }`}
                  >
                    <p className="font-medium text-gray-900 truncate">{doc.filename}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                        doc.status === 'ready' ? 'bg-green-100 text-green-700' :
                        doc.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                        doc.status === 'failed' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {doc.status}
                      </span>
                      <span className="text-xs text-gray-400">
                        {doc.page_count} pages
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Chunks panel */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            {!selectedDoc ? (
              <div className="text-center text-gray-400 py-12">
                <p>Select a document to view its chunks</p>
              </div>
            ) : chunksLoading ? (
              <LoadingSpinner size="sm" message="Loading chunks..." />
            ) : (
              <>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Chunks ({chunks.length})
                </h2>
                {chunks.length === 0 ? (
                  <p className="text-sm text-gray-500">No chunks found for this document.</p>
                ) : (
                  <div className="space-y-3 max-h-[700px] overflow-y-auto">
                    {chunks.map((chunk) => (
                      <div
                        key={chunk.id}
                        className="bg-gray-50 rounded-lg border border-gray-200 p-4"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-medium text-indigo-600">
                            Chunk #{chunk.chunk_index}
                          </span>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs text-gray-400">
                              {chunk.token_count} tokens
                            </span>
                            <span
                              className={`text-xs px-1.5 py-0.5 rounded-full ${
                                chunk.has_embedding
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-yellow-100 text-yellow-700'
                              }`}
                            >
                              {chunk.has_embedding ? 'Embedded' : 'No embedding'}
                            </span>
                          </div>
                        </div>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-6">
                          {chunk.content}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
