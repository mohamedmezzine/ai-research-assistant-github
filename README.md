# MEZZINE AI Research Assistant

A local-first AI research workspace for uploading PDF papers, indexing them with vector embeddings, and asking grounded questions with source citations. The project combines a FastAPI backend, PostgreSQL with pgvector, a static chat interface, Gemini cloud models, and optional local AI providers through Ollama and SentenceTransformers.

## Features

- PDF upload with background ingestion
- Page-level text extraction and chunking
- Image extraction with generated image descriptions for multimodal retrieval
- Vector search over paper chunks with PostgreSQL and pgvector
- Streaming chat responses with cited sources
- Saved chat sessions and message history
- Selectable research workflows: summarize, methodology, contributions, limitations, gap finder, compare, and literature review
- AI mode selector for cloud, hybrid, and private/local operation
- Built-in PDF viewer for citation inspection

## Technical Report

A detailed technical report describing the architecture, implementation choices, and project workflow is available here: [Technical Report](docs/ai_research_assitant.pdf).

## Architecture

```text
Frontend SPA
  |
  | HTTP / streaming NDJSON
  v
FastAPI backend
  |
  |-- papers API -> PDF extraction -> chunking -> embeddings
  |-- chat API   -> query embedding -> vector retrieval -> LLM answer
  |-- sessions   -> persisted chat history
  v
PostgreSQL + pgvector
```

The backend is organized around clear modules:

- `backend/app/api`: FastAPI routers for papers, chat, and sessions
- `backend/app/rag`: PDF loading, chunking, ingestion, and retrieval
- `backend/app/llm`: provider abstraction for Gemini, Ollama, and local embeddings
- `backend/app/core`: application settings
- `backend/app/db.py`: database connection pooling and startup migrations
- `frontend`: browser UI, chat logic, PDF viewer, and styling

## Tech Stack

- Python 3.10+
- FastAPI and Uvicorn
- PostgreSQL 16 with pgvector
- Gemini API for cloud chat, embeddings, and vision
- Ollama for local chat generation
- SentenceTransformers for local embeddings
- PyMuPDF and Pillow for PDF/image processing
- Vanilla HTML, CSS, and JavaScript frontend
- Docker Compose for the database

## AI Modes

| Mode | Embeddings | Chat generation | Privacy profile |
| --- | --- | --- | --- |
| `cloud` | Gemini | Gemini | Best cloud quality, documents are processed through cloud AI services |
| `hybrid` | Local SentenceTransformers | Gemini | Full documents are indexed locally, retrieved chunks are sent to Gemini |
| `private` | Local SentenceTransformers | Ollama | Documents and questions are processed locally, assuming local models are installed |

Changing embedding mode requires re-indexing uploaded papers because cloud and local embeddings are stored separately.

## Quick Start

### 1. Configure environment variables

Create a local environment file from the example:

```powershell
Copy-Item .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

Edit `.env` and set `GEMINI_API_KEY` for cloud or hybrid mode. Do not commit real `.env` files.

### 2. Start PostgreSQL with pgvector

```bash
docker compose up -d db
```

The database is exposed locally on port `5433`.

### 3. Create and activate a Python environment

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

For `hybrid` or `private` mode, install the optional local embedding dependencies listed in `backend/requirements.txt`.

### 5. Run the application

```bash
python -m uvicorn app.main:app --reload
```

Open the app at:

```text
http://127.0.0.1:8000
```

API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Local Private Mode

Install Ollama, then pull the configured local model:

```bash
ollama pull llama3.1:8b
```

Set the local mode values in `.env`:

```env
AI_MODE=private
LOCAL_CHAT_PROVIDER=ollama
LOCAL_CHAT_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_EMBEDDING_PROVIDER=sentence_transformers
LOCAL_EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
```

Then install the optional local embedding dependencies and restart the backend.

## Environment Variables

The project reads configuration from `.env` at the repository root or `backend/.env`.

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Required for Gemini cloud chat, embeddings, and image descriptions |
| `DATABASE_URL` | PostgreSQL connection string |
| `UPLOAD_DIR` | Directory for uploaded PDFs |
| `AI_MODE` | One of `cloud`, `hybrid`, or `private` |
| `CLOUD_CHAT_PROVIDER` | Cloud chat provider, currently `gemini` |
| `CLOUD_CHAT_MODEL` | Gemini chat model name |
| `CLOUD_EMBEDDING_PROVIDER` | Cloud embedding provider, currently `gemini` |
| `CLOUD_EMBEDDING_MODEL` | Gemini embedding model name |
| `LOCAL_CHAT_PROVIDER` | Local chat provider, currently `ollama` |
| `LOCAL_CHAT_MODEL` | Ollama model name |
| `OLLAMA_BASE_URL` | Local Ollama API base URL |
| `LOCAL_EMBEDDING_PROVIDER` | Local embedding provider, currently `sentence_transformers` |
| `LOCAL_EMBEDDING_MODEL` | SentenceTransformers model name |

## API Overview

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/papers` | List indexed papers for the active mode |
| `POST` | `/papers/upload` | Upload a PDF and start background ingestion |
| `DELETE` | `/papers/{paper_id}` | Delete a paper and its chunks |
| `GET` | `/sessions` | List chat sessions |
| `POST` | `/sessions` | Create a chat session |
| `GET` | `/sessions/{session_id}/chat` | Load session messages |
| `PUT` | `/sessions/{session_id}` | Rename a session |
| `DELETE` | `/sessions/{session_id}` | Delete a session |
| `POST` | `/chat` | Return a complete answer |
| `POST` | `/chat/stream` | Stream an answer as NDJSON |
| `GET` | `/settings/ai-mode` | Read active AI mode |
| `PUT` | `/settings/ai-mode` | Update active AI mode |

## Security Notes

- Real secrets belong only in `.env` or `backend/.env`; both are ignored by Git.
- `.env.example` contains placeholders only.
- Uploaded PDFs and extracted images are ignored by Git under `data/papers` and `data/images`.
- The app is designed for local development. Add authentication, stricter CORS, upload limits, and production secret management before public deployment.

## Project Status

This is an MVP research assistant suitable for local demos and portfolio development. Recommended next improvements:

- Add a real pytest suite for chunking, prompts, providers, and API flows
- Add ingestion status tracking for background jobs
- Restrict CORS for deployed environments
- Add upload size validation
- Add retrieval and answer quality evaluation metrics
- Move from global AI mode mutation to per-session or per-upload mode capture
