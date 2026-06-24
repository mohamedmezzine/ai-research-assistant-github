# Feature Specification: Privacy Mode with Local AI Models

## Project

**NexusAI Research Assistant**

## Feature Name

**Privacy Mode: Local LLM and Local Embeddings**

---

## 1. Feature Objective

The goal of this feature is to allow NexusAI users to work with sensitive research documents without sending their knowledge base to external cloud APIs.

Currently, the system uses cloud AI providers such as Gemini for embeddings and answer generation. This is useful for quality and speed, but it may not be acceptable when users upload confidential documents such as:

- unpublished research papers
- internal company reports
- medical or legal documents
- private R&D notes
- thesis drafts
- client documents
- sensitive business knowledge bases

This feature introduces a **local/private mode** where both document embeddings and chat generation can run locally on the user's machine.

---

## 2. Why This Feature Matters

This feature improves the project from a standard RAG chatbot into a more professional AI research workspace.

It adds value in four important areas:

| Area | Value |
|---|---|
| Privacy | Sensitive documents can stay on the local machine |
| Flexibility | Users can choose between cloud quality and local privacy |
| Professional AI engineering | Shows provider abstraction and modular architecture |
| CV impact | Demonstrates cloud/local AI deployment awareness |

The key idea is:

```text
Cloud Mode     = better quality and easier setup
Private Mode   = better privacy and local control
```

---

## 3. Privacy Modes

The system should support three AI modes.

### 3.1 Cloud Mode

In this mode, both embeddings and chat generation use cloud APIs.

```text
Embeddings: Gemini
Chat model: Gemini
Privacy level: Low
```

Use case:

- normal research papers
- public PDFs
- non-sensitive documents
- best answer quality

---

### 3.2 Hybrid Mode

In this mode, document embeddings are generated locally, but retrieved text chunks are still sent to a cloud LLM for answer generation.

```text
Embeddings: Local
Chat model: Gemini
Privacy level: Medium
```

Use case:

- user wants to avoid sending the full document during indexing
- user accepts sending only retrieved chunks to the cloud model
- useful compromise between privacy and answer quality

Important note:

> Hybrid Mode is not fully private because the final retrieved chunks are still sent to a cloud API.

---

### 3.3 Full Private Mode

In this mode, both embeddings and chat generation are local.

```text
Embeddings: Local SentenceTransformers
Chat model: Local Ollama model
Privacy level: High
```

Use case:

- confidential documents
- internal company data
- private research
- offline or local-only usage

Important note:

> For real privacy, both embeddings and chat generation must be local.

---

## 4. Recommended Local Stack

### Local Chat Generation

Use **Ollama** to run local language models.

Example local models:

```text
llama3.1:8b
mistral:7b
phi3:mini
qwen2.5:7b
gemma2:2b
```

Recommended first model:

```text
llama3.1:8b
```

If the machine is weak, start with:

```text
phi3:mini
```

---

### Local Embeddings

Use **SentenceTransformers** for local embeddings.

Recommended first embedding model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

This model outputs 384-dimensional vectors.

Alternative models:

```text
sentence-transformers/all-mpnet-base-v2
BAAI/bge-small-en-v1.5
BAAI/bge-base-en-v1.5
```

---

## 5. Important Vector Dimension Warning

The current project uses PostgreSQL + pgvector.

If the current embedding column is:

```sql
embedding vector(3072)
```

then it is compatible with 3072-dimensional Gemini embeddings.

However, local embedding models may produce different dimensions:

| Model | Vector dimension |
|---|---:|
| Gemini embedding model | often 3072 |
| all-MiniLM-L6-v2 | 384 |
| all-mpnet-base-v2 | 768 |
| bge-small-en-v1.5 | 384 |
| bge-base-en-v1.5 | 768 |

Because pgvector columns have a fixed vector size, embeddings from different models cannot be mixed in the same column unless they have the same dimension.

### MVP Decision

For the first version, NexusAI should use **one active embedding mode at a time**.

When switching from cloud embeddings to local embeddings, the user must re-index documents.

Frontend warning:

```text
Changing the embedding provider requires re-indexing your uploaded papers.
```

---

## 6. Proposed Architecture

Instead of calling Gemini directly inside the RAG pipeline, we introduce a provider abstraction.

### Current style

```text
pipeline.py
   └── directly calls gemini/openai client
```

### New style

```text
pipeline.py
   └── provider factory
          ├── GeminiProvider
          ├── OllamaProvider
          └── LocalEmbeddingProvider
```

Recommended folder structure:

```text
backend/
└── app/
    ├── llm/
    │   ├── base.py
    │   ├── gemini_provider.py
    │   ├── ollama_provider.py
    │   ├── local_embeddings.py
    │   └── factory.py
    │
    ├── rag/
    │   ├── pipeline.py
    │   ├── chunker.py
    │   └── pdf_loader.py
    │
    ├── core/
    │   └── config.py
    │
    └── main.py
```

---

## 7. Environment Variables

Update `.env` to support provider switching.

```env
# Main AI mode
AI_MODE=cloud

# Cloud settings
CLOUD_CHAT_PROVIDER=gemini
CLOUD_CHAT_MODEL=gemini-1.5-flash
CLOUD_EMBEDDING_PROVIDER=gemini
CLOUD_EMBEDDING_MODEL=text-embedding-004

# Local chat settings
LOCAL_CHAT_PROVIDER=ollama
LOCAL_CHAT_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434

# Local embedding settings
LOCAL_EMBEDDING_PROVIDER=sentence_transformers
LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/research_assistant
```

Allowed values for `AI_MODE`:

```text
cloud
hybrid
private
```

---

## 8. Backend Implementation Plan

### Step 1: Add Provider Base Classes

Create:

```text
backend/app/llm/base.py
```

Suggested structure:

```python
from abc import ABC, abstractmethod


class ChatProvider(ABC):
    @abstractmethod
    def generate_answer(self, question: str, contexts: list[dict]) -> str:
        pass


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        pass

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]
```

---

### Step 2: Move Gemini Logic into a Provider

Create:

```text
backend/app/llm/gemini_provider.py
```

Responsibilities:

- generate Gemini embeddings
- generate Gemini chat answers
- preserve current cloud behavior

The existing Gemini code from `openai_client.py` or `gemini_client.py` should be moved here.

---

### Step 3: Add Ollama Chat Provider

Create:

```text
backend/app/llm/ollama_provider.py
```

Responsibilities:

- call local Ollama server
- send prompt and retrieved context
- return local model response

Example request target:

```text
http://localhost:11434/api/generate
```

Expected local model:

```text
llama3.1:8b
```

Before using the feature, the user should run:

```bash
ollama pull llama3.1:8b
ollama run llama3.1:8b
```

---

### Step 4: Add Local Embedding Provider

Create:

```text
backend/app/llm/local_embeddings.py
```

Responsibilities:

- load SentenceTransformers model
- encode document chunks locally
- encode user questions locally
- normalize vectors for similarity search

Install dependency:

```bash
pip install sentence-transformers
```

Add to `requirements.txt`:

```text
sentence-transformers
```

---

### Step 5: Add Provider Factory

Create:

```text
backend/app/llm/factory.py
```

The factory should decide which providers to use depending on `AI_MODE`.

Expected behavior:

| AI_MODE | Chat provider | Embedding provider |
|---|---|---|
| cloud | Gemini | Gemini |
| hybrid | Gemini | Local SentenceTransformers |
| private | Ollama | Local SentenceTransformers |

---

### Step 6: Update RAG Pipeline

Modify:

```text
backend/app/rag/pipeline.py
```

Replace direct Gemini calls with provider calls.

Instead of:

```python
embedding = gemini_embed_text(text)
answer = gemini_generate_answer(question, contexts)
```

Use:

```python
from app.llm.factory import get_chat_provider, get_embedding_provider

embedding_provider = get_embedding_provider()
chat_provider = get_chat_provider()

embedding = embedding_provider.embed_text(text)
answer = chat_provider.generate_answer(question, contexts)
```

---

### Step 7: Add AI Mode Status Endpoint

Add endpoint:

```http
GET /settings/ai-mode
```

Example response:

```json
{
  "ai_mode": "private",
  "chat_provider": "ollama",
  "chat_model": "llama3.1:8b",
  "embedding_provider": "sentence_transformers",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "privacy_level": "full_private",
  "requires_reindex": true
}
```

This endpoint will help the frontend show the current mode.

---

## 9. Frontend Implementation Plan

### 9.1 Add AI Mode Badge

Display a badge in the UI header:

```text
Mode: Cloud Gemini
```

or:

```text
Mode: Private Local
```

Suggested colors:

| Mode | Badge |
|---|---|
| Cloud | Blue |
| Hybrid | Orange |
| Private | Green |

---

### 9.2 Add Privacy Notice

When private mode is active, show:

```text
Private Mode Active — documents and questions are processed locally.
```

When hybrid mode is active, show:

```text
Hybrid Mode Active — embeddings are local, but retrieved chunks are sent to the cloud chat model.
```

When cloud mode is active, show:

```text
Cloud Mode Active — documents are processed using cloud AI services.
```

---

### 9.3 Add Re-index Warning

If the user changes embedding provider, show:

```text
Changing embedding provider requires re-indexing your uploaded papers.
```

---

## 10. Database Strategy

### MVP Strategy

Use one embedding provider at a time.

If the user changes from Gemini embeddings to local embeddings:

1. Clear old chunks and embeddings.
2. Keep paper metadata if possible.
3. Ask user to re-index PDFs.

### More Advanced Strategy

Later, support multiple embedding providers by separating chunks from embeddings:

```text
papers
paper_chunks
chunk_embeddings
```

Suggested advanced schema:

```sql
CREATE TABLE paper_chunks (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER REFERENCES papers(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INTEGER
);

CREATE TABLE chunk_embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES paper_chunks(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Note:

> Because pgvector requires fixed vector dimensions, a separate table or separate database may be needed for each embedding dimension.

---

## 11. User Experience Flow

### Cloud Mode Flow

```text
1. User uploads PDF
2. Gemini creates embeddings
3. Chunks are stored in PostgreSQL + pgvector
4. User asks a question
5. Gemini generates an answer from retrieved chunks
```

### Private Mode Flow

```text
1. User starts Ollama locally
2. User selects AI_MODE=private
3. User uploads PDF
4. SentenceTransformers creates embeddings locally
5. Chunks are stored in PostgreSQL + pgvector
6. User asks a question
7. Ollama generates an answer locally
```

---

## 12. Error Handling

Add clear errors for:

| Problem | User-friendly message |
|---|---|
| Ollama is not running | Local AI server is not running. Please start Ollama and try again. |
| Local model missing | Local model not found. Please run `ollama pull <model_name>`. |
| Embedding dimension mismatch | Current database vector size does not match the selected embedding model. Please re-index your documents. |
| Gemini quota exceeded | Cloud AI quota exceeded. Try again later or switch to Private Mode. |
| No papers indexed | Please upload and index at least one PDF before asking questions. |

---

## 13. Acceptance Criteria

This feature is complete when:

- [ ] User can run the app in `AI_MODE=cloud`
- [ ] User can run the app in `AI_MODE=private`
- [ ] Private mode uses Ollama for chat generation
- [ ] Private mode uses SentenceTransformers for embeddings
- [ ] Frontend displays the current AI mode
- [ ] Backend exposes `GET /settings/ai-mode`
- [ ] The app warns users when re-indexing is required
- [ ] Cloud mode still works as before
- [ ] No cloud API is called in Full Private Mode
- [ ] README explains how to install and start Ollama

---

## 14. Verification Plan

### Test 1: Cloud Mode

```env
AI_MODE=cloud
```

Expected:

- PDF upload works
- embeddings are generated using Gemini
- chat answer is generated using Gemini
- frontend badge shows Cloud Mode

---

### Test 2: Private Mode

```env
AI_MODE=private
```

Expected:

- PDF upload works
- embeddings are generated locally
- chat answer is generated through Ollama
- frontend badge shows Private Mode
- app works without calling Gemini

---

### Test 3: Ollama Not Running

Stop Ollama and ask a question.

Expected result:

```text
Local AI server is not running. Please start Ollama and try again.
```

---

### Test 4: Embedding Dimension Mismatch

Switch from cloud embeddings to local embeddings without re-indexing.

Expected result:

```text
Embedding dimension mismatch. Please re-index your documents.
```

---

## 15. README Section to Add

Add this section to the project README:

```markdown
## Privacy Mode: Local AI

NexusAI supports a private local mode for sensitive research documents.

### Cloud Mode

Uses Gemini API for embeddings and answer generation.

### Private Mode

Uses local embeddings through SentenceTransformers and local chat generation through Ollama.

To use Private Mode:

1. Install Ollama.
2. Pull a local model:

`ollama pull llama3.1:8b`

3. Update `.env`:

```env
AI_MODE=private
LOCAL_CHAT_MODEL=llama3.1:8b
LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

4. Restart the backend.

In Private Mode, documents and questions are processed locally.
```

---

## 16. CV Bullet

After implementing this feature, use this bullet in your CV:

```text
Implemented a dual-mode AI architecture supporting both cloud-based Gemini inference and privacy-preserving local inference using Ollama and SentenceTransformers, enabling sensitive research documents to be processed without sending content to external APIs.
```

---

## 17. Future Improvements

Possible later improvements:

- user-selectable AI mode from the frontend
- per-session AI mode
- per-workspace AI mode
- multiple embedding indexes
- local reranker model
- local citation verifier
- offline Docker Compose mode
- GPU acceleration support
- model benchmarking dashboard
- cost and latency comparison between cloud and local modes
