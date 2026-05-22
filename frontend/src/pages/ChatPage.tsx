import { useState, useEffect, useRef, useCallback } from 'react';
import { askQuestionStream, listDocuments, getChatHistory, listSessions } from '../services/api';
import type { SourceChunk, Document, ChatMessage, SessionSummary } from '../types';
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
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [showSidebar, setShowSidebar] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const streamingRef = useRef('');
  const abortRef = useRef<AbortController | null>(null);

  const loadSessions = useCallback(() => {
    listSessions().then((data) => setSessions(data.sessions)).catch(() => {});
  }, []);

  useEffect(() => {
    listDocuments().then((data) => setDocuments(data.documents)).catch(() => {});
    loadSessions();
  }, [loadSessions]);

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

  const startNewChat = () => {
    setSessionId(undefined);
    setMessages([]);
    setStreamingAnswer('');
    setError(null);
  };

  const loadSession = async (sid: string) => {
    setSessionId(sid);
    setMessages([]);
    setStreamingAnswer('');
    setError(null);
    try {
      const data = await getChatHistory(sid);
      setMessages(data.messages);
    } catch {
      setError('Failed to load session');
    }
  };

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
        loadSessions();
      },
      (err) => {
        clearTimeout(timeoutId);
        setError(err.message);
        setLoading(false);
      }
    );

    setQuestion('');
  }, [question, loading, sessionId, selectedDocId, loadSessions]);

  function formatDate(d: string) {
    const date = new Date(d);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  }

  return (
    <div className="flex gap-4 h-[calc(100vh-9rem)]">
      {/* Session sidebar */}
      {showSidebar && (
        <div className="w-64 shrink-0 bg-white rounded-xl border border-gray-200 flex flex-col">
          <div className="p-3 border-b border-gray-100">
            <button
              onClick={startNewChat}
              className="w-full px-3 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
            >
              + New Chat
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {sessions.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-4">No conversations yet</p>
            )}
            {sessions.map((s) => (
              <button
                key={s.session_id}
                onClick={() => loadSession(s.session_id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  s.session_id === sessionId
                    ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                    : 'text-gray-700 hover:bg-gray-50 border border-transparent'
                }`}
              >
                <p className="font-medium truncate">{s.preview || 'New conversation'}</p>
                <p className="text-xs text-gray-400 mt-0.5">{formatDate(s.last_message_at)}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">
            {sessionId ? 'Chat' : 'Ask Questions'}
          </h1>
          <button
            onClick={() => setShowSidebar(!showSidebar)}
            className="text-sm text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100"
          >
            {showSidebar ? 'Hide history' : 'Show history'}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="mb-3 text-xs text-gray-400 text-center">
            The model may take 30-60 seconds to respond on first use (cold start).
          </div>
        )}

        <div className="mb-3">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Filter by document
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

        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-3 flex-1 overflow-y-auto">
          {messages.length === 0 && !loading && (
            <div className="text-center text-gray-400 py-12">
              <svg className="mx-auto h-12 w-12 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p>Ask a question about your documents</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`mb-4 ${msg.role === 'user' ? 'text-right' : ''}`}>
              <div className={`inline-block max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
              {msg.sources && msg.sources.length > 0 && msg.role === 'assistant' && (
                <SourcePanel sources={msg.sources as unknown as SourceChunk[]} />
              )}
            </div>
          ))}

          {streamingAnswer && (
            <div className="mb-4">
              <div className="inline-block max-w-[80%] bg-gray-100 rounded-xl px-4 py-3 text-sm whitespace-pre-wrap">
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
    </div>
  );
}
