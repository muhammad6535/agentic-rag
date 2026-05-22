import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function HomePage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Enterprise Knowledge Assistant
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          Upload your documents, ask questions, and get grounded answers based
          only on your data — powered by RAG, LangChain, and pgvector.
        </p>
        <div className="flex justify-center space-x-4">
          {isAuthenticated ? (
            <>
              <Link
                to="/upload"
                className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
              >
                Upload Documents
              </Link>
              <Link
                to="/chat"
                className="inline-flex items-center px-6 py-3 bg-white text-indigo-600 font-medium rounded-lg border border-indigo-600 hover:bg-indigo-50 transition-colors"
              >
                Ask Questions
              </Link>
            </>
          ) : (
            <>
              <Link
                to="/register"
                className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
              >
                Get Started
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center px-6 py-3 bg-white text-indigo-600 font-medium rounded-lg border border-indigo-600 hover:bg-indigo-50 transition-colors"
              >
                Sign In
              </Link>
            </>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6 py-8">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2">1. Ingest Documents</h3>
          <p className="text-gray-600 text-sm">
            Upload PDF or TXT files. The system extracts text, splits it into
            chunks, generates embeddings, and stores everything in PostgreSQL
            with pgvector.
          </p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2">2. Retrieve Context</h3>
          <p className="text-gray-600 text-sm">
            Ask questions in natural language. The system finds the most relevant
            chunks using vector similarity search with cosine distance.
          </p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2">3. Generate Answers</h3>
          <p className="text-gray-600 text-sm">
            LangChain sends the retrieved context to the LLM, which generates
            answers grounded only in your documents with source citations.
          </p>
        </div>
      </div>

      <div className="bg-indigo-50 rounded-xl p-8 border border-indigo-100 my-8">
        <h2 className="text-2xl font-bold text-indigo-900 mb-4">
          How It Works
        </h2>
        <div className="space-y-4 text-indigo-800">
          <p>
            <strong>RAG (Retrieval-Augmented Generation)</strong> combines
            retrieval from a knowledge base with LLM generation. Instead of
            relying on the model's training data, we first retrieve relevant
            document chunks, then feed them as context to the LLM.
          </p>
          <p className="text-sm text-indigo-600">
            Tech stack: FastAPI + LangChain + PostgreSQL/pgvector + Ollama + React + Tailwind CSS + Docker
          </p>
        </div>
      </div>
    </div>
  );
}
