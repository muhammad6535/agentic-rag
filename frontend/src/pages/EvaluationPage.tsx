import { useState, useEffect, useCallback } from 'react';
import { runEvaluation, getEvalHistory, getEvalSummary, listDocuments } from '../services/api';
import type { EvalRunResponse, EvalSummaryResponse, Document } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';

function ScoreBar({ label, score }: { label: string; score: number; color?: string }) {
  const pct = Math.round(score * 100);
  const bg = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-500">{pct}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div className={`h-2.5 rounded-full ${bg}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ScoreCard({ title, result }: { title: string; result: EvalRunResponse }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">{title}</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            {new Date(result.created_at).toLocaleString()}
            {result.document_name && ` — ${result.document_name}`}
          </p>
        </div>
        <span className={`text-lg font-bold ml-3 ${result.overall_score >= 0.7 ? 'text-green-600' : result.overall_score >= 0.4 ? 'text-yellow-600' : 'text-red-600'}`}>
          {Math.round(result.overall_score * 100)}%
        </span>
      </div>
      <ScoreBar label="Faithfulness" score={result.faithfulness_score} />
      <ScoreBar label="Answer Relevance" score={result.answer_relevance_score} />
      <ScoreBar label="Context Relevance" score={result.context_relevance_score} />
      <ScoreBar label="Hallucination (lower is better)" score={1 - result.hallucination_score} />
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-sm text-indigo-600 hover:text-indigo-800 mt-2"
      >
        {expanded ? 'Hide details' : 'Show details'}
      </button>
      {expanded && (
        <div className="mt-4 space-y-3 border-t pt-3">
          <div>
            <p className="text-sm font-medium text-gray-700 mb-1">Question</p>
            <p className="text-sm text-gray-600 bg-gray-50 rounded p-2">{result.question}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700 mb-1">Answer</p>
            <p className="text-sm text-gray-600 bg-gray-50 rounded p-2">{result.answer}</p>
          </div>
          {result.unsupported_claims.length > 0 && (
            <div>
              <p className="text-sm font-medium text-red-600 mb-1">Unsupported Claims ({result.unsupported_claims.length})</p>
              {result.unsupported_claims.map((c, i) => (
                <p key={i} className="text-sm text-red-700 bg-red-50 rounded p-2 mb-1">"{c.claim}"</p>
              ))}
            </div>
          )}
          {result.supported_claims.length > 0 && (
            <div>
              <p className="text-sm font-medium text-green-600 mb-1">Supported Claims ({result.supported_claims.length})</p>
              {result.supported_claims.slice(0, 5).map((c, i) => (
                <p key={i} className="text-sm text-green-700 bg-green-50 rounded p-2 mb-1">"{c.claim}"</p>
              ))}
            </div>
          )}
          {result.sources_used.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-1">Sources Used</p>
              {result.sources_used.map((s, i) => (
                <div key={i} className="text-xs text-gray-500 bg-gray-50 rounded p-2 mb-1">
                  <span className="font-medium">{s.document_name}</span> Chunk {s.chunk_index} — relevance: {Math.round(s.score * 100)}%
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function EvaluationPage() {
  const [question, setQuestion] = useState('');
  const [selectedDocId, setSelectedDocId] = useState('');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [running, setRunning] = useState(false);
  const [currentResult, setCurrentResult] = useState<EvalRunResponse | null>(null);
  const [summary, setSummary] = useState<EvalSummaryResponse | null>(null);
  const [history, setHistory] = useState<EvalRunResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'run' | 'history'>('run');

  const fetchAll = useCallback(async () => {
    try {
      const [docs, sum, hist] = await Promise.all([
        listDocuments(),
        getEvalSummary(),
        getEvalHistory(),
      ]);
      setDocuments(docs.documents.filter((d) => d.status === 'ready'));
      setSummary(sum);
      setHistory(hist.evaluations);
    } catch {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || running) return;
    setRunning(true);
    setError(null);
    setCurrentResult(null);
    try {
      const result = await runEvaluation(question.trim(), selectedDocId || undefined);
      setCurrentResult(result);
      // Refresh history
      const [sum, hist] = await Promise.all([getEvalSummary(), getEvalHistory()]);
      setSummary(sum);
      setHistory(hist.evaluations);
      setTab('history');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Evaluation failed');
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading evaluation panel..." />;

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">RAG Evaluation</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">{error}</div>
      )}

      {/* Summary Dashboard */}
      {summary && summary.total_evaluations > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Aggregate Scores ({summary.total_evaluations} evaluations)</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { label: 'Faithfulness', score: summary.avg_faithfulness },
              { label: 'Answer Relevance', score: summary.avg_answer_relevance },
              { label: 'Context Relevance', score: summary.avg_context_relevance },
              { label: 'Hallucination (↓)', score: summary.avg_hallucination },
              { label: 'Overall', score: summary.avg_overall },
            ].map((m) => (
              <div key={m.label} className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-900">{Math.round(m.score * 100)}%</p>
                <p className="text-xs text-gray-500 mt-1">{m.label}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-1 mb-6 border-b border-gray-200">
        <button
          onClick={() => setTab('run')}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${tab === 'run' ? 'bg-white text-indigo-600 border border-b-0 border-gray-200' : 'text-gray-500 hover:text-gray-700'}`}
        >
          Run Evaluation
        </button>
        <button
          onClick={() => setTab('history')}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${tab === 'history' ? 'bg-white text-indigo-600 border border-b-0 border-gray-200' : 'text-gray-500 hover:text-gray-700'}`}
        >
          History ({history.length})
        </button>
      </div>

      {tab === 'run' && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl border border-gray-200 p-5 sticky top-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Run Evaluation</h2>
              <form onSubmit={handleRun} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Question</label>
                  <textarea
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    rows={3}
                    placeholder="Enter a question to evaluate..."
                    disabled={running}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Filter by document (optional)</label>
                  <select
                    value={selectedDocId}
                    onChange={(e) => setSelectedDocId(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
                    disabled={running}
                  >
                    <option value="">All documents</option>
                    {documents.map((d) => (
                      <option key={d.id} value={d.id}>{d.filename}</option>
                    ))}
                  </select>
                </div>
                <button
                  type="submit"
                  disabled={running || !question.trim()}
                  className="w-full px-4 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {running ? 'Running Evaluation...' : 'Run Evaluation'}
                </button>
              </form>
              {running && (
                <div className="mt-4 text-center text-sm text-gray-500">
                  Generating answer and running LLM-as-judge evaluation...
                </div>
              )}
            </div>
          </div>
          <div className="lg:col-span-3">
            {currentResult && <ScoreCard title="Latest Result" result={currentResult} />}
            {!currentResult && !running && (
              <div className="text-center text-gray-400 py-12 bg-white rounded-xl border border-gray-200">
                <svg className="mx-auto h-12 w-12 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <p>Enter a question and run an evaluation</p>
                <p className="text-xs mt-1">The system will generate an answer, then evaluate it for faithfulness, relevance, and hallucination</p>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'history' && (
        <div>
          {history.length === 0 ? (
            <div className="text-center text-gray-400 py-12 bg-white rounded-xl border border-gray-200">
              <p>No evaluations yet. Run your first evaluation above.</p>
            </div>
          ) : (
            history.map((r) => (
              <ScoreCard
                key={r.id}
                title={r.question.length > 80 ? r.question.slice(0, 80) + '...' : r.question}
                result={r}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
