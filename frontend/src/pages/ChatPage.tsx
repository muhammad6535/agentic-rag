import { useState, useEffect, useRef, useCallback } from 'react';
import { askQuestionStream, listDocuments, getChatHistory } from '../services/api';
import type { SourceChunk, Document, ChatMessage } from '../types';
import SourcePanel from '../components/SourcePanel';
import LoadingSpinner from '../components/LoadingSpinner';

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export default function ChatPage() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [streamingAnswer, setStreamingAnswer] = useState('');
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const streamingRef = useRef('');
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    listDocuments().then((data) => setDocuments(data.documents)).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingAnswer]);

  useEffect(() => {
    if (sessionId && messages.length === 0) {
      getChatHistory(sessionId).then((data) => {
        setMessages(data.messages);
      }).catch(() => {});
    }
  }, [sessionId]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: genId(),
      session_id: sessionId || '',
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError(null);
    setStreamingAnswer('');
    streamingRef.current = '';

    const request = {
      question: question.trim(),
      session_id: sessionId,
      document_id: selectedDocId || undefined,
    };

    // Timeout safety net — if stream doesn't finish in 120s, show error
    const timeoutId = setTimeout(() => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
      setLoading(false);
      setError('Request timed out. The model may still be loading. Please try again.');
    }, 120000);

    abortRef.current = askQuestionStream(
      request,
      (token) => {
        streamingRef.current += token;
        setStreamingAnswer(streamingRef.current);
      },
      (data) => {
        clearTimeout(timeoutId);
        setSessionId(data.session_id);
        const fullAnswer = streamingRef.current;
        streamingRef.current = '';
        setStreamingAnswer('');
        setMessages((prev) => [
          ...prev,
          {
            id: genId(),
            session_id: data.session_id,
            role: 'assistant',
            content: fullAnswer,
            sources: data.sources as SourceChunk[],
            created_at: new Date().toISOString(),
          },
        ]);
        setLoading(false);
      },
      (err) => {
        clearTimeout(timeoutId);
        setError(err.message);
        setLoading(false);
      }
    );

    setQuestion('');
  }, [question, loading, sessionId, selectedDocId]);

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Ask Questions</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      {loading && (
        <div className="mb-4 text-xs text-gray-400 text-center">
          The model may take 30-60 seconds to respond on first use (cold start).
        </div>
      )}

      {/* Document filter */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Filter by document (optional)
        </label>
        <select
          value={selectedDocId}
          onChange={(e) => setSelectedDocId(e.target.value)}
          className="w-full max-w-xs rounded-lg border-gray-300 border px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">All documents</option>
          {documents
            .filter((d) => d.status === 'ready')
            .map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename}
              </option>
            ))}
        </select>
      </div>

      {/* Messages */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4 min-h-[400px] max-h-[600px] overflow-y-auto">
        {messages.length === 0 && !loading && (
          <div className="text-center text-gray-400 py-12">
            <svg className="mx-auto h-12 w-12 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <p>Ask a question about your documents</p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`mb-4 ${msg.role === 'user' ? 'text-right' : ''}`}
          >
            <div
              className={`inline-block max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              {msg.content}
            </div>
            {msg.sources && msg.sources.length > 0 && msg.role === 'assistant' && (
              <SourcePanel sources={msg.sources as unknown as SourceChunk[]} />
            )}
          </div>
        ))}

        {streamingAnswer && (
          <div className="mb-4">
            <div className="inline-block max-w-[80%] bg-gray-100 rounded-xl px-4 py-3 text-sm">
              {streamingAnswer}
              <span className="animate-pulse">|</span>
            </div>
          </div>
        )}

        {loading && !streamingAnswer && (
          <LoadingSpinner size="sm" message="Thinking..." />
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex space-x-3">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Type your question here..."
          className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  );
}
