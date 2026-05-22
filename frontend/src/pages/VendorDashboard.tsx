import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getVendorDashboard, listVendorAssessments, uploadVendorDocument } from '../services/api';
import type { VendorAssessment } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';

function RiskBadge({ level }: { level?: string | null }) {
  const colors: Record<string, string> = {
    Critical: 'bg-red-100 text-red-800',
    High: 'bg-orange-100 text-orange-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    Low: 'bg-green-100 text-green-800',
  };
  const c = colors[level || ''] || 'bg-gray-100 text-gray-800';
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${c}`}>{level || 'N/A'}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending_review: 'bg-blue-100 text-blue-800',
    approved: 'bg-green-100 text-green-800',
    rejected: 'bg-red-100 text-red-800',
  };
  const labels: Record<string, string> = {
    pending_review: 'Pending Review',
    approved: 'Approved',
    rejected: 'Rejected',
  };
  const c = colors[status] || 'bg-gray-100 text-gray-800';
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${c}`}>{labels[status] || status}</span>;
}

export default function VendorDashboard() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [assessments, setAssessments] = useState<VendorAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('');

  const fetchData = useCallback(async () => {
    try {
      const [dash, list] = await Promise.all([
        getVendorDashboard(),
        listVendorAssessments({ status: filter || undefined }),
      ]);
      setDashboard(dash);
      setAssessments(list.assessments);
    } catch {
      setError('Failed to load vendor data');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadVendorDocument(file);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading vendor dashboard..." />;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">AI Vendor Risk Copilot</h1>
        <div className="flex items-center space-x-3">
          <label className="relative cursor-pointer">
            <span className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors">
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              {uploading ? 'Processing...' : 'Upload Vendor Doc'}
            </span>
            <input type="file" className="hidden" accept=".pdf,.txt" onChange={handleUpload} disabled={uploading} />
          </label>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">{error}</div>
      )}

      {uploading && (
        <div className="mb-6 p-4 bg-indigo-50 border border-indigo-200 rounded-lg text-sm text-indigo-700">
          AI is analyzing the document... extracting vendor info, classifying risk, and drafting next steps.
        </div>
      )}

      {/* Summary cards */}
      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-2xl font-bold text-gray-900">{dashboard.total_assessments}</p>
            <p className="text-xs text-gray-500 mt-1">Total Vendors</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-2xl font-bold text-red-600">{dashboard.critical_count + dashboard.high_count}</p>
            <p className="text-xs text-gray-500 mt-1">High Risk</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-2xl font-bold text-blue-600">{dashboard.pending_review}</p>
            <p className="text-xs text-gray-500 mt-1">Pending Review</p>
          </div>
          <Link to="/vendors/approval" className="bg-white rounded-xl border border-gray-200 p-4 hover:border-indigo-300 transition-colors">
            <p className="text-2xl font-bold text-indigo-600">{dashboard.approved_count}</p>
            <p className="text-xs text-gray-500 mt-1">Approved →</p>
          </Link>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex space-x-1 mb-4">
        {['', 'pending_review', 'approved', 'rejected'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              filter === f ? 'bg-indigo-100 text-indigo-700' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            }`}
          >
            {f ? f.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : 'All'}
          </button>
        ))}
      </div>

      {/* Assessments list */}
      {assessments.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
          <p className="text-gray-500 mb-2">No vendor assessments yet</p>
          <p className="text-sm text-gray-400">Upload a vendor document to get started</p>
        </div>
      ) : (
        <div className="space-y-3">
          {assessments.map((a) => (
            <Link
              key={a.id}
              to={`/vendors/${a.id}`}
              className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-indigo-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    <h3 className="font-semibold text-gray-900 truncate">
                      {a.company_name || a.original_filename}
                    </h3>
                    <RiskBadge level={a.risk_level} />
                    <StatusBadge status={a.status} />
                  </div>
                  <p className="text-xs text-gray-500">
                    {a.original_filename}
                    {a.risk_type && ` — ${a.risk_type}`}
                    {a.country && ` — ${a.country}`}
                  </p>
                </div>
                <svg className="w-5 h-5 text-gray-400 ml-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
              {a.next_steps.length > 0 && (
                <p className="text-xs text-gray-400 mt-2 truncate">{a.next_steps[0]}</p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
