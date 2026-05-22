import axios from 'axios';
import type {
  DocumentList,
  ChunkList,
  AskRequest,
  AskResponse,
  ChatHistory,
  SessionListResponse,
  EvaluationResponse,
  TokenResponse,
  LoginRequest,
  RegisterRequest,
  User,
  EvalRunResponse,
  EvalHistoryResponse,
  EvalSummaryResponse,
  VendorDashboardData,
  VendorAssessment,
  VendorDetail,
  VendorListResponse,
  AuditEntry,
} from '../types';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const login = async (data: LoginRequest): Promise<TokenResponse> => {
  const response = await api.post('/auth/login', data);
  return response.data;
};

export const register = async (data: RegisterRequest): Promise<TokenResponse> => {
  const response = await api.post('/auth/register', data);
  return response.data;
};

export const getMe = async (): Promise<User> => {
  const response = await api.get('/auth/me');
  return response.data;
};

// Documents
export const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const listDocuments = async (skip = 0, limit = 50): Promise<DocumentList> => {
  const response = await api.get('/documents', { params: { skip, limit } });
  return response.data;
};

export const getDocument = async (id: string) => {
  const response = await api.get(`/documents/${id}`);
  return response.data;
};

export const getDocumentChunks = async (
  id: string,
  skip = 0,
  limit = 100
): Promise<ChunkList> => {
  const response = await api.get(`/documents/${id}/chunks`, {
    params: { skip, limit },
  });
  return response.data;
};

// Chat
export const askQuestion = async (request: AskRequest): Promise<AskResponse> => {
  const response = await api.post('/chat/ask', request);
  return response.data;
};

export const askQuestionStream = (
  request: AskRequest,
  onToken: (token: string) => void,
  onDone: (data: { session_id: string; sources: unknown[] }) => void,
  onError: (error: Error) => void
): AbortController => {
  const controller = new AbortController();
  const token = localStorage.getItem('token');

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  fetch(`${API_BASE}/chat/ask/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      const decoder = new TextDecoder();
      let buffer = '';
      let doneCalled = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6);
            if (payload.startsWith('[DONE]')) {
              doneCalled = true;
              const metadata = JSON.parse(payload.slice(6));
              onDone(metadata);
            } else {
              onToken(payload);
            }
          }
        }
      }

      if (!doneCalled) {
        onDone({ session_id: '', sources: [] });
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err);
      }
    });

  return controller;
};

export const getChatHistory = async (
  sessionId: string,
  limit = 100,
  offset = 0
): Promise<ChatHistory> => {
  const response = await api.get('/chat/history', {
    params: { session_id: sessionId, limit, offset },
  });
  return response.data;
};

export const listSessions = async (skip = 0, limit = 50): Promise<SessionListResponse> => {
  const response = await api.get('/chat/sessions', { params: { skip, limit } });
  return response.data;
};

// Evaluation
export const evaluateGroundedness = async (
  question: string,
  documentId?: string
): Promise<EvaluationResponse> => {
  const response = await api.post('/evaluate/groundedness', {
    question,
    document_id: documentId || null,
  });
  return response.data;
};

export const runEvaluation = async (
  question: string,
  documentId?: string
): Promise<EvalRunResponse> => {
  const response = await api.post('/evaluate/run', {
    question,
    document_id: documentId || null,
  });
  return response.data;
};

export const getEvalHistory = async (
  skip = 0,
  limit = 20
): Promise<EvalHistoryResponse> => {
  const response = await api.get('/evaluate/history', { params: { skip, limit } });
  return response.data;
};

export const getEvalSummary = async (): Promise<EvalSummaryResponse> => {
  const response = await api.get('/evaluate/summary');
  return response.data;
};

// Vendor Risk Copilot
export const uploadVendorDocument = async (file: File): Promise<VendorAssessment> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/vendors/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const listVendorAssessments = async (params?: {
  status?: string;
  risk_level?: string;
  skip?: number;
  limit?: number;
}): Promise<VendorListResponse> => {
  const response = await api.get('/vendors', { params });
  return response.data;
};

export const getVendorDashboard = async (): Promise<VendorDashboardData> => {
  const response = await api.get('/vendors/dashboard');
  return response.data;
};

export const getVendorDetail = async (id: string): Promise<VendorDetail> => {
  const response = await api.get(`/vendors/${id}`);
  return response.data;
};

export const approveVendorAssessment = async (
  id: string,
  approved: boolean,
  notes?: string
): Promise<VendorAssessment> => {
  const response = await api.post(`/vendors/${id}/approve`, { approved, notes });
  return response.data;
};

export const getAuditLog = async (id: string): Promise<AuditEntry[]> => {
  const response = await api.get(`/vendors/${id}/audit`);
  return response.data;
};
