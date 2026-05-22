import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  getVendorDetail,
  approveVendorAssessment,
} from '../services/api';
import type { VendorDetail } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';

function RiskBadge({ level }: { level?: string | null }) {
  const colors: Record<string, string> = {
    Critical: 'bg-red-100 text-red-800',
    High: 'bg-orange-100 text-orange-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    Low: 'bg-green-100 text-green-800',
  };
  return <span className={`text-sm font-semibold px-2.5 py-1 rounded-full ${colors[level || ''] || 'bg-gray-100 text-gray-800'}`}>{level || 'N/A'}</span>;
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="mb-3">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="text-sm text-gray-900 mt-0.5">{value || '—'}</p>
    </div>
  );
}

export default function VendorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [assessment, setAssessment] = useState<VendorDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getVendorDetail(id);
      setAssessment(data);
      setNotes(data.human_notes || '');
    } catch {
      setError('Failed to load assessment');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetch(); }, [fetch]);

  const handleApprove = async (approved: boolean) => {
    if (!id) return;
    setActionLoading(true);
    setError(null);
    try {
      await approveVendorAssessment(id, approved, notes);
      await fetch();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading assessment..." />;
  if (!assessment) return <div className="text-center text-gray-500 py-12">Assessment not found</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center space-x-3 mb-6">
        <Link to="/vendors" className="text-sm text-indigo-600 hover:text-indigo-800">← Back to Dashboard</Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-bold text-gray-900 truncate">
          {assessment.company_name || assessment.original_filename}
        </h1>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">{error}</div>
      )}

      {/* Status bar */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <span className="text-sm text-gray-500">Status:</span>
          <span className={`text-sm font-semibold px-2.5 py-1 rounded-full ${
            assessment.status === 'approved' ? 'bg-green-100 text-green-800' :
            assessment.status === 'rejected' ? 'bg-red-100 text-red-800' :
            'bg-blue-100 text-blue-800'
          }`}>
            {assessment.status.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
          </span>
          <RiskBadge level={assessment.risk_level} />
        </div>
        <span className="text-xs text-gray-400">{new Date(assessment.created_at).toLocaleString()}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Extracted info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Extracted data */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Extracted Information</h2>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Company Name" value={assessment.company_name} />
              <Field label="Risk Type" value={assessment.risk_type} />
              <Field label="Country" value={assessment.country} />
              <Field label="Business Unit" value={assessment.business_unit} />
            </div>
            <div className="mt-3">
              <Field label="Compliance Notes" value={assessment.compliance_notes} />
            </div>
            {assessment.missing_fields.length > 0 && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-xs font-medium text-yellow-800 mb-1">Missing Fields (AI detected)</p>
                <ul className="text-xs text-yellow-700 list-disc list-inside">
                  {assessment.missing_fields.map((f, i) => <li key={i}>{f}</li>)}
                </ul>
              </div>
            )}
          </div>

          {/* AI-Suggested Next Steps */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">AI-Suggested Next Steps</h2>
            {assessment.next_steps.length === 0 ? (
              <p className="text-sm text-gray-400">No next steps suggested.</p>
            ) : (
              <ol className="space-y-2">
                {assessment.next_steps.map((step, i) => (
                  <li key={i} className="flex items-start space-x-2 text-sm text-gray-700">
                    <span className="flex-shrink-0 w-5 h-5 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-xs font-medium mt-0.5">
                      {i + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            )}
          </div>

          {/* AI-Drafted Email */}
          {assessment.follow_up_email && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">AI-Drafted Follow-Up Email</h2>
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap font-mono">
                {assessment.follow_up_email}
              </div>
            </div>
          )}

          {/* Audit Log */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Audit Trail</h2>
            {assessment.audit_log.length === 0 ? (
              <p className="text-sm text-gray-400">No audit entries yet.</p>
            ) : (
              <div className="space-y-2">
                {assessment.audit_log.map((entry) => (
                  <div key={entry.id} className="flex items-start space-x-3 text-sm">
                    <div className="w-2 h-2 mt-1.5 rounded-full bg-indigo-400 flex-shrink-0" />
                    <div>
                      <span className="font-medium text-gray-700">{entry.action.replace(/_/g, ' ')}</span>
                      <span className="text-gray-400 ml-2">{new Date(entry.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Actions */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5 sticky top-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Human Review</h2>

            {assessment.status === 'pending_review' ? (
              <>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Review Notes</label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    rows={4}
                    placeholder="Add any notes, concerns, or changes..."
                    disabled={actionLoading}
                  />
                </div>
                <button
                  onClick={() => handleApprove(true)}
                  disabled={actionLoading}
                  className="w-full px-4 py-2.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors mb-2"
                >
                  {actionLoading ? 'Processing...' : '✓ Approve & Log'}
                </button>
                <button
                  onClick={() => handleApprove(false)}
                  disabled={actionLoading}
                  className="w-full px-4 py-2.5 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  ✕ Reject & Request Changes
                </button>
              </>
            ) : (
              <div className={`p-3 rounded-lg text-sm ${
                assessment.status === 'approved' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}>
                {assessment.status === 'approved'
                  ? 'This assessment has been approved.'
                  : 'This assessment has been rejected.'}
                {assessment.human_notes && (
                  <p className="mt-2 text-xs">Notes: {assessment.human_notes}</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
