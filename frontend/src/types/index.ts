export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  page_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentList {
  documents: Document[];
  total: number;
}

export interface Chunk {
  id: string;
  document_id: string;
  content: string;
  chunk_index: number;
  token_count: number;
  has_embedding: boolean;
  created_at: string;
}

export interface ChunkList {
  chunks: Chunk[];
  total: number;
}

export interface SourceChunk {
  id: string;
  content: string;
  document_name: string;
  chunk_index: number;
  score: number;
}

export interface AskRequest {
  question: string;
  session_id?: string;
  document_id?: string;
}

export interface AskResponse {
  answer: string;
  session_id: string;
  sources: SourceChunk[];
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  document_id?: string | null;
  sources?: SourceChunk[] | null;
  created_at: string;
}

export interface ChatHistory {
  messages: ChatMessage[];
  total: number;
}

export interface SessionSummary {
  session_id: string;
  last_message_at: string;
  preview: string;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
  total: number;
}

// ---- Evaluation types ----
export interface EvalClaimItem {
  claim: string;
  supported: boolean;
  evidence?: string | null;
}

export interface EvalRunResponse {
  id: string;
  question: string;
  answer: string;
  document_name?: string | null;
  faithfulness_score: number;
  answer_relevance_score: number;
  context_relevance_score: number;
  hallucination_score: number;
  overall_score: number;
  supported_claims: EvalClaimItem[];
  unsupported_claims: EvalClaimItem[];
  sources_used: Array<{
    id: string;
    document_name: string;
    chunk_index: number;
    content_preview: string;
    score: number;
  }>;
  created_at: string;
}

export interface EvalHistoryResponse {
  evaluations: EvalRunResponse[];
  total: number;
}

export interface EvalSummaryResponse {
  total_evaluations: number;
  avg_faithfulness: number;
  avg_answer_relevance: number;
  avg_context_relevance: number;
  avg_hallucination: number;
  avg_overall: number;
  recent_evaluations: EvalRunResponse[];
}

export interface EvaluationResponse {
  question: string;
  answer: string;
  sources_used: number;
  has_content: boolean;
  groundedness_score: number;
  sources: Array<{
    id: string;
    document_name: string;
    chunk_index: number;
    content_preview: string;
  }>;
}

// ---- Vendor Risk Copilot types ----
export interface VendorDashboardData {
  total_assessments: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  pending_review: number;
  approved_count: number;
  recent_assessments: VendorAssessment[];
}

export interface VendorAssessment {
  id: string;
  original_filename: string;
  company_name?: string | null;
  risk_type?: string | null;
  risk_level?: string | null;
  country?: string | null;
  business_unit?: string | null;
  compliance_notes?: string | null;
  missing_fields: string[];
  next_steps: string[];
  follow_up_email?: string | null;
  status: string;
  created_at: string;
}

export interface VendorDetail extends VendorAssessment {
  extracted_raw: Record<string, unknown>;
  human_notes?: string | null;
  updated_at: string;
  audit_log: AuditEntry[];
}

export interface AuditEntry {
  id: string;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface VendorListResponse {
  assessments: VendorAssessment[];
  total: number;
}
