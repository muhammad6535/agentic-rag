# Enterprise Knowledge Assistant

A production-grade **Agentic RAG** application with LLM evaluation and a **Vendor Risk Copilot**. Upload documents, ask questions with multi-query retrieval and self-reflection, evaluate answer quality, and automate vendor risk assessments — all running locally with open-source models.

## Features

- **Agentic RAG Pipeline** — Query rewriting, multi-query retrieval with RRF fusion, LLM-based reranking, and self-reflection loops for complete answers
- **Authentication** — User registration and JWT-based session management
- **User-Scoped Documents** — Each user sees and queries only their own documents
- **PDF/TXT Ingestion** — Extract, chunk, embed, and store with full pipeline status tracking
- **Semantic Search** — Vector similarity retrieval via pgvector (cosine distance, IVFFlat index)
- **Streaming Responses** — Real-time token-by-token answer streaming via Server-Sent Events
- **Source Citations** — Every answer cites the document and chunk that provided each piece of information
- **Chat History** — Persistent conversation sessions with per-user isolation
- **LLM-as-Judge Evaluation** — Faithfulness, answer relevance, context relevance, and hallucination scoring
- **Vendor Risk Copilot** — Upload vendor documents → AI extracts structured data, classifies risk (Critical/High/Medium/Low), generates next steps, drafts follow-up emails, with human-in-the-loop approval workflow and full audit trail
- **Fully Containerized** — One command to start everything with Docker Compose
- **Open-Source Stack** — Ollama for LLM + embeddings, no API keys required

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI |
| AI Framework | LangChain |
| Database | PostgreSQL 16 + pgvector |
| LLM | Ollama (llama3.2:3b) |
| Embeddings | Ollama (nomic-embed-text) |
| Frontend | React 18 + TypeScript |
| Styling | Tailwind CSS |
| Auth | JWT (HS256) + bcrypt |
| Containerization | Docker + Docker Compose |

## Architecture

```
                         ┌──────────────┐
                         │   Frontend    │
                         │  React + TS   │
                         └──────┬───────┘
                                │ HTTP / SSE
                         ┌──────▼───────┐
                         │    Nginx     │
                         │  (proxy +    │
                         │   static)    │
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │   Backend    │
                         │   FastAPI    │
                         └──────┬───────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
   ┌──────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
   │  PostgreSQL  │      │   Ollama    │      │   File      │
   │  + pgvector  │      │  (LLM +     │      │   Storage   │
   │  (chunks,    │      │  embed)     │      │  (uploads/) │
   │   messages)  │      └─────────────┘      └─────────────┘
   └─────────────┘

   Pipeline (Agentic RAG):
   Query → Rewrite (3 variants) → Multi-Query Search → RRF Merge
        → LLM Rerank → Generate Answer → Self-Reflection → (loop if incomplete)
   
   Vendor Risk Copilot:
   Upload Doc → AI Extract → Risk Classify → Next Steps → Draft Email
        → Human Review → Approve/Reject → Audit Trail

   Evaluation:
   Q&A Pair → LLM-as-Judge → Faithfulness / Relevance / Hallucination Scores
```

## Project Structure

```
rag-project/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config.py                  # Environment config (pydantic-settings)
│   │   ├── database.py                # Async SQLAlchemy engine + session
│   │   ├── models/                    # SQLAlchemy ORM
│   │   │   ├── user.py                # Users table
│   │   │   ├── document.py            # Documents + Chunks (pgvector)
│   │   │   └── chat.py                # Chat messages
│   │   ├── schemas/                   # Pydantic request/response models
│   │   │   ├── auth.py                # Auth schemas
│   │   │   ├── document.py            # Document schemas
│   │   │   └── chat.py                # Chat + session schemas
│   │   ├── services/                  # Business logic
│   │   │   ├── auth_service.py        # JWT + password hashing
│   │   │   ├── document_loader.py     # PDF/TXT text extraction
│   │   │   ├── text_splitter.py       # RecursiveCharacter splitting
│   │   │   ├── embedding_service.py   # Vector embedding generation
│   │   │   ├── retrieval_service.py   # pgvector similarity search
│   │   │   ├── qa_service.py          # LLM answer generation
│   │   │   ├── agentic_rag_service.py # Query rewrite, multi-query, rerank, reflect
│   │   │   ├── evaluation_service.py  # LLM-as-judge scoring
│   │   │   ├── vendor_service.py      # Vendor extraction, classification, email
│   │   │   └── chat_history_service.py# Message persistence
│   │   ├── models/                    # SQLAlchemy ORM
│   │   │   ├── evaluation.py          # Evaluation results
│   │   │   └── vendor.py              # Vendor assessments + audit log
│   │   └── routes/                    # API route handlers
│   │       ├── auth.py                # Register, login, me
│   │       ├── documents.py           # Upload, list, view
│   │       ├── chat.py                # Ask (streaming + non-streaming), history
│   │       ├── evaluation.py          # LLM-as-judge evaluation
│   │       └── vendors.py             # Vendor Risk Copilot endpoints
│   ├── startup.py                     # Dep wait + model warm-up
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── context/
│   │   │   └── AuthContext.tsx         # Auth state management
│   │   ├── components/
│   │   │   ├── Navbar.tsx
│   │   │   ├── ProtectedRoute.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── SourcePanel.tsx
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   ├── UploadPage.tsx
│   │   │   ├── ChatPage.tsx
│   │   │   └── AdminPage.tsx
│   │   ├── services/api.ts            # Axios client + auth interceptor
│   │   ├── types/index.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── Dockerfile (multi-stage)
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── docker-compose.yml                  # 4 services: db, ollama, backend, frontend
├── init.sql                            # Schema with pgvector IVFFlat index
├── .env.example
└── README.md
```

## Quick Start

### Prerequisites

- Docker + Docker Compose

### 1. Clone and Configure

```bash
git clone <repo-url> rag-project
cd rag-project
cp .env.example .env
```

### 2. Start Everything

```bash
docker compose up --build
```

The startup script will:
1. Wait for PostgreSQL and Ollama to become healthy
2. Pull the required models (llama3.2:3b, nomic-embed-text) — ~2.5 GB on first run
3. Pre-warm the LLM model to eliminate cold-start latency
4. Start the FastAPI backend (port 8000)
5. Serve the React frontend via Nginx (port 5173)

**First startup** takes 2–5 minutes depending on download speeds.

### 3. Use the Application

Open **http://localhost:5173**

1. **Create an account** — Register with email, username, and password
2. **Upload documents** — PDF or TXT files up to 50 MB each
3. **Ask questions** — Agentic RAG with query rewriting, multi-query retrieval, and self-reflection. Streaming and non-streaming modes available.
4. **Evaluate answers** — LLM-as-Judge evaluates faithfulness, relevance, and hallucination
5. **Vendor Risk Copilot** — Upload vendor documents → AI extracts risk data, classifies risk level, generates next steps & emails → Approve/Reject with audit trail

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account (returns JWT) |
| POST | `/api/auth/login` | Sign in (returns JWT) |
| GET | `/api/auth/me` | Current user info (requires auth) |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload` | Upload PDF/TXT (requires auth) |
| GET | `/api/documents` | List user's documents |
| GET | `/api/documents/{id}` | Get document details |
| GET | `/api/documents/{id}/chunks` | Get document chunks |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/ask` | Ask question (non-streaming) |
| POST | `/api/chat/ask/stream` | Ask question (SSE streaming) |
| GET | `/api/chat/history?session_id=...` | Get session history |
| GET | `/api/chat/sessions` | List user's sessions |

### Evaluation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/evaluate/run` | Run LLM-as-Judge evaluation |
| GET | `/api/evaluate/history` | List past evaluations |
| GET | `/api/evaluate/summary` | Aggregate scores summary |

### Vendor Risk Copilot

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/vendors/upload` | Upload vendor document for AI assessment |
| GET | `/api/vendors` | List vendor assessments (with status/risk filters) |
| GET | `/api/vendors/dashboard` | Summary counts by risk level and status |
| GET | `/api/vendors/{id}` | Full detail with AI output + audit log |
| POST | `/api/vendors/{id}/approve` | Human approve/reject with notes |
| GET | `/api/vendors/{id}/audit` | Audit trail entries |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Service health check |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `llama3.2:3b` | Ollama model for generation |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `CHUNK_SIZE` | `1000` | Characters per text chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between adjacent chunks |
| `TOP_K_RETRIEVAL` | `4` | Number of chunks to retrieve |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum upload file size |
| `JWT_SECRET` | (see .env) | Secret key for JWT signing |
| `JWT_EXPIRE_HOURS` | `24` | Token expiration time |

## Commands

```bash
# Start all services
docker compose up -d

# Rebuild and start
docker compose up --build -d

# View logs
docker compose logs -f backend

# Stop services
docker compose down

# Stop and delete data (volumes)
docker compose down -v

# Scale the backend (horizontal)
docker compose up -d --scale backend=3
```

## Design Decisions

- **Ollama over OpenAI**: Fully offline, no API keys, no per-token costs. Uses `llama3.2:3b` (2B params) for fast CPU inference or `llama3.2:1b` for even lighter deployments.
- **pgvector over Pinecone/Weaviate**: Keeps vectors alongside relational data in the same PostgreSQL instance; no external vector DB dependency.
- **Agentic RAG**: Uses query rewriting (3 variants) + multi-query retrieval + Reciprocal Rank Fusion + LLM reranking + self-reflection loops — goes beyond simple retrieve-and-generate.
- **LLM-as-Judge**: The same local model evaluates faithfulness and hallucination, keeping the stack fully self-contained.
- **Vendor Risk Copilot**: A complete business workflow — AI extraction → classification → recommendation → human approval → audit trail — all in one system.
- **Separate streaming endpoint**: The `/ask/stream` endpoint uses SSE while `/ask` returns a single JSON response, letting clients choose between simplicity and real-time UX.
- **User isolation**: All document and chat queries include `user_id` filters at the database level; no user can access another user's data.
- **No ORM migrations**: The `init.sql` script runs on first database startup. For production, consider Alembic or similar.

## License

MIT
