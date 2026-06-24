# Project Critic Review (v2 — Post-Refactor)

> **Review Date:** 2026-06-24  
> **Reviewer:** Senior AI Software Architect  
> **Project:** MEZZINE_AI Research Assistant (Agentic RAG)  
> **Scope:** Full re-analysis after major refactoring

---

## 1. Executive Summary

### What Changed Since v1

You addressed **many** of the critical issues from the first review. Here is a summary of what was fixed:

| Issue from v1 | Status |
|---|---|
| No `.gitignore` | ✅ Fixed — comprehensive and well-organized |
| Real API keys in `.env.example` | ✅ Fixed — now contains placeholder |
| `requirements.txt` incomplete | ✅ Fixed — accurate, categorized, with optional local mode deps |
| Prompt duplication (100+ lines × 2) | ✅ Fixed — extracted to `llm/prompts.py` |
| `generate_answer_stream` missing from base class | ✅ Fixed — both methods now abstract with `history` param |
| `pipeline.py` god module (304 lines) | ✅ Fixed — split into `ingest.py`, `retrieval.py`, `crud_papers.py`, `crud_sessions.py` |
| No API routers (everything in `main.py`) | ✅ Fixed — `api/papers.py`, `api/sessions.py`, `api/chat.py` |
| No connection pooling | ✅ Fixed — `psycopg_pool.ConnectionPool` with fallback |
| Sync PDF ingestion blocking event loop | ✅ Fixed — `BackgroundTasks` used in upload endpoint |
| No conversation history in prompts | ✅ Fixed — `get_recent_history()` with truncation |
| No similarity threshold | ✅ Fixed — `WHERE similarity > 0.05` in retrieval |
| Naive character-based chunking | ✅ Fixed — paragraph-first, then sentence, then word splitting |
| Local model too weak (llama3.2:1b) | ✅ Fixed — default changed to `llama3.1:8b` |
| Vision module not integrated | ✅ Fixed — `generate_image_description()` called during ingestion |
| No `__init__.py` | ⚠️ Partial — only in `api/`, missing in `app/`, `core/`, `llm/`, `rag/` |

**Verdict: This is a significant improvement.** The codebase went from a monolithic prototype to a properly structured application. The architecture is now clean enough to show in a portfolio code review.

### What Remains Weak

- **CORS still allows `*`** (was called out in v1, not fixed)
- **No upload size limit** — `await file.read()` still loads entire file into memory
- **No `__init__.py`** in most Python packages (only `api/` has one)
- **`psycopg-pool` missing from `requirements.txt`** — code imports it but it's not listed
- **20 test scripts scattered in `backend/`** — `test_db.py` through `test_db15.py` are debug scripts, not real tests
- **`settings.ai_mode` mutation still not thread-safe**
- **No git commits yet** — `master` has zero commits
- **Still no real test suite** (pytest, proper assertions, mocking)
- **Still no RAG evaluation**
- **`test-ingest` debug endpoint exposed in production**

---

## 2. Current Architecture Understanding

### Project Structure (Post-Refactor)

```
ai-research-assistant/
  backend/
    app/
      api/
        __init__.py             # Only __init__.py in the project
        papers.py               # Paper CRUD + upload + BackgroundTasks
        sessions.py             # Session CRUD router
        chat.py                 # Chat + streaming endpoints
      core/
        config.py               # Pydantic settings (well-organized)
      llm/
        base.py                 # ChatProvider + EmbeddingProvider ABCs
        factory.py              # Mode-aware provider factory
        prompts.py              # Shared prompts for all 7 modes
        gemini_provider.py      # Gemini chat + embeddings (no duplication)
        ollama_provider.py      # Ollama chat (no duplication)
        local_embeddings.py     # SentenceTransformers embeddings
        vision.py               # Image description (Gemini/Moondream)
      rag/
        ingest.py               # PDF ingestion + embedding + image description
        retrieval.py            # Vector search with similarity threshold
        chunker.py              # Semantic paragraph/sentence-aware chunking
        pdf_loader.py           # PyMuPDF text + image extraction
      crud_papers.py            # Papers DB operations
      crud_sessions.py          # Sessions + chat history DB operations
      db.py                     # ConnectionPool + migrations
      main.py                   # Slim FastAPI app (107 lines, routers included)
    init.sql                    # Schema with image_path + ai_mode columns
    requirements.txt            # Categorized, pinned, with optional deps
    test_db.py ... test_db15.py # Debug scripts (20 files, not real tests)
    test_extract.py, test_ingest.py, test_pdf.py, test_upload.py
    .env                        # Environment config (gitignored)
  frontend/
    index.html                  # SPA with mode selector, PDF viewer
    app.js                      # 581 lines — chat, sessions, upload, streaming
    pdf_viewer.js               # PDF.js rendering + text highlighting
    styles.css                  # Dark theme CSS design system (857 lines)
    test.txt                    # Residual test file
  data/
    papers/                     # PDF uploads (gitignored)
    images/                     # Extracted images (gitignored)
  docs/
    architecture.md             # Still a placeholder (6 lines)
  .gitignore                    # Comprehensive
  .env.example                  # Placeholder values only
  docker-compose.yml            # pgvector container
  privacy_mode_local_llm_feature.md
  README.md
```

### Backend Architecture

FastAPI app with **proper router separation**:
- `api/papers.py` — upload with `.pdf` validation, BackgroundTasks for ingestion, CRUD
- `api/sessions.py` — session management
- `api/chat.py` — sync + streaming chat with conversation history

Business logic is **cleanly separated**:
- `rag/ingest.py` — ingestion pipeline (PDF → chunks → embeddings → DB)
- `rag/retrieval.py` — vector search with similarity threshold
- `crud_papers.py` / `crud_sessions.py` — database operations
- `llm/prompts.py` — single source of truth for all 7 mode prompts

Database layer uses **connection pooling** (`psycopg_pool.ConnectionPool`) with a graceful fallback to direct connections.

### Key Flows

**PDF Upload:** Frontend → `POST /papers/upload` → validate `.pdf` extension → save file → create paper record (sync) → `BackgroundTasks.add_task(ingest_pdf)` → return immediately with paper ID

**Ingestion (Background):** Extract pages (text + images) → for each image, generate description via `vision.py` → chunk text semantically → batch embed → store in appropriate column (`embedding_cloud` or `embedding_local`)

**Chat (Streaming):** Embed question → cosine similarity search with `WHERE similarity > 0.05` → get recent conversation history → build mode-specific prompt → stream response via NDJSON → save to chat_logs

**Mode Switching:** Frontend dropdown → `PUT /settings/ai-mode` → mutates `settings.ai_mode` → affects which embedding column is used and which chat/embedding provider is selected

---

## 3. Strengths

| # | Strength | Details |
|---|----------|---------|
| 1 | **Clean module separation** | God module eliminated. Each file has a single responsibility |
| 2 | **Shared prompts** | `prompts.py` is the single source of truth — no more duplication |
| 3 | **Abstract base class is complete** | Both `generate_answer` and `generate_answer_stream` with `history` param |
| 4 | **Background ingestion** | `BackgroundTasks` means uploads return instantly |
| 5 | **Connection pooling** | `ConnectionPool(min_size=2, max_size=10)` with fallback |
| 6 | **Conversation history** | `get_recent_history()` with 500-char truncation prevents context explosion |
| 7 | **Similarity threshold** | `WHERE similarity > 0.05` filters out irrelevant noise |
| 8 | **Semantic chunking** | Paragraph → sentence → word splitting with overlap |
| 9 | **Multimodal ingestion** | Images are now described and indexed during ingestion |
| 10 | **Proper API routers** | `papers`, `sessions`, `chat` with tags and prefixes |
| 11 | **Mode-aware paper filtering** | `get_all_papers()` filters by `ai_mode` column |
| 12 | **Upgraded local model** | `llama3.1:8b` is viable for research analysis |
| 13 | **Proper `.gitignore`** | Covers `.env`, venvs, caches, IDE files, data dirs |
| 14 | **Clean `.env.example`** | No real keys leaked |
| 15 | **Well-organized requirements** | Categorized sections, optional local deps commented |

---

## 4. Critical Problems

### Problem 1: `psycopg-pool` Missing from `requirements.txt`

- **File:** `backend/requirements.txt`
- **What is wrong:** `db.py` imports `from psycopg_pool import ConnectionPool` (line 3), but `psycopg-pool` is not listed in `requirements.txt`. A clean `pip install -r requirements.txt` will crash on import.
- **Why it matters:** Breaks deployment from scratch. This is the same category of issue as the missing `google-genai` from v1 — reproducibility.
- **Suggested fix:** Add `psycopg-pool==3.1.7` to the Database section of `requirements.txt`.

### Problem 2: CORS Still Allows All Origins

- **File:** `backend/app/main.py` (line 29)
- **What is wrong:** `allow_origins=["*"]` with `allow_credentials=True`. The code even has a comment saying "Update CORS to be more restrictive based on Critic Review" but the change was never made.
- **Why it matters:** Any website can make authenticated requests to your API if deployed.
- **Suggested fix:** `allow_origins=["http://127.0.0.1:8000", "http://localhost:8000", "http://127.0.0.1:5500"]`

### Problem 3: Debug Endpoint Exposed in Production

- **File:** `backend/app/main.py` (lines 83–97)
- **What is wrong:** `/test-ingest` endpoint exists that: (a) forces `settings.ai_mode = "hybrid"`, (b) ingests the latest PDF without auth, (c) returns full tracebacks. This is a security and stability risk.
- **Why it matters:** Anyone can trigger expensive ingestion. Full tracebacks leak internal paths and code structure.
- **Suggested fix:** Remove it entirely, or gate it behind `if settings.debug:` and environment variable.

### Problem 4: No Upload File Size Limit

- **File:** `backend/app/api/papers.py` (line 32)
- **What is wrong:** `await file.read()` loads the entire uploaded file into memory. A 2GB upload will crash the server. The `.pdf` extension check from v1 is now implemented (good!), but there's no size check.
- **Why it matters:** OOM crash risk. Easy denial-of-service.
- **Suggested fix:**
  ```python
  MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
  content = await file.read()
  if len(content) > MAX_UPLOAD_SIZE:
      raise HTTPException(413, "File too large. Maximum size is 100 MB.")
  ```

### Problem 5: Missing `__init__.py` in Most Packages

- **Files:** Missing in `app/`, `app/core/`, `app/llm/`, `app/rag/`
- **What is wrong:** Only `app/api/__init__.py` exists. The other packages work because of how Python resolves imports from the working directory, but this is fragile.
- **Why it matters:** Will break if you ever package the app, run tests from a different directory, or use tools like `mypy` or `pytest` discovery.
- **Suggested fix:** Create empty `__init__.py` in all four directories.

### Problem 6: `settings.ai_mode` Mutation Is Not Thread-Safe

- **File:** `backend/app/main.py` (line 48)
- **What is wrong:** `settings.ai_mode = request.mode.lower()` mutates a global singleton. If two requests hit `/settings/ai-mode` simultaneously, or a user changes mode while ingestion is running in a background task, the behavior is unpredictable.
- **Why it matters:** Background ingestion could start in "cloud" mode and finish embedding in "hybrid" mode mid-way through if the user switches modes during processing.
- **Suggested fix:** For now, add a comment documenting the limitation. Long-term: pass `ai_mode` as a parameter to `ingest_pdf()` captured at upload time.

### Problem 7: `vector_to_sql()` Duplicated Between `ingest.py` and `retrieval.py`

- **Files:** `backend/app/rag/ingest.py` (line 11), `backend/app/rag/retrieval.py` (line 5)
- **What is wrong:** The same utility function is copy-pasted in two files.
- **Why it matters:** If the format changes (e.g., for a pgvector upgrade), you must update both.
- **Suggested fix:** Move to a shared utility, e.g., `app/db.py` or `app/utils.py`.

### Problem 8: 20 Debug Test Scripts Polluting `backend/`

- **Files:** `backend/test_db.py` through `backend/test_db15.py`, `test_extract.py`, `test_ingest.py`, `test_pdf.py`, `test_upload.py`
- **What is wrong:** These are ad-hoc debug scripts (e.g., `test_db.py` just runs a SELECT and prints results). They are not unit tests. They clutter the project root.
- **Why it matters:** An interviewer will see these and question your testing discipline. They suggest trial-and-error debugging rather than systematic testing.
- **Suggested fix:** Delete all of them. Replace with a proper `backend/tests/` directory with pytest tests (see Section 11).

### Problem 9: No Git Commits

- **What is wrong:** `git log` shows "your current branch 'master' does not have any commits yet." The project has a `.git` directory but zero commits.
- **Why it matters:** You lose all history of your improvements. You can't show the evolution of the codebase. You can't demonstrate the refactoring you did.
- **Suggested fix:** Make your first commit now. Then commit after each logical change with a descriptive message.

### Problem 10: `OPENAI_API_KEY` Still in `.env`

- **File:** `backend/.env` (line 2)
- **What is wrong:** The `.env` file still contains an `OPENAI_API_KEY` variable, even though OpenAI is not used anywhere in the codebase. While `.env` is gitignored, this is confusing.
- **Why it matters:** Suggests unused dependencies. Confuses future contributors.
- **Suggested fix:** Remove the `OPENAI_API_KEY` line from `.env`.

---

## 5. RAG Pipeline Review

### PDF Parsing Quality

**Unchanged from v1** — still MVP-level. PyMuPDF `get_text("text")` works for text-heavy PDFs but struggles with multi-column layouts, tables, and equations.

**New positive:** Images are now described via `vision.py` and indexed as `[IMAGE] Description: ...` chunks. This is a genuine multimodal improvement.

### Chunking Strategy — SIGNIFICANTLY IMPROVED

The new `chunker.py` is a major upgrade:

| Aspect | v1 | v2 |
|--------|----|----|
| Strategy | Fixed 1200-char windows | Paragraph → sentence → word |
| Boundary awareness | None (split mid-word) | Respects paragraph and sentence boundaries |
| Overlap | Fixed 200-char | Smart overlap with sentence boundary search |
| Large paragraph handling | Not handled | Falls back to sentence splitting |
| Very long sentence handling | Not handled | Hard truncation as last resort |
| Max chunk size | 1200 chars | 1500 chars |

**Remaining issue:** The overlap logic on line 27 (`overlap_text.find('. ')`) searches forward (not backward) for a period, which may not find the best sentence boundary. `rfind` would be more appropriate. Also, the overlap text is taken from the *end* of the current chunk but then searches for the *first* period — this can result in very short or very long overlap.

### Retrieval Quality — IMPROVED

- **Similarity threshold added:** `WHERE similarity > 0.05` filters out irrelevant results. However, 0.05 is very low — most cosine similarity scores for unrelated content are already 0.1–0.3. A threshold of 0.2–0.3 would be more effective at filtering noise.
- **Chunk IDs now returned** in retrieval results (good for traceability).
- **SQL injection risk reduced** — `target_column` is still interpolated via f-string, but the values come from a controlled `if/else` on `settings.ai_mode`.

### Embedding Flow — IMPROVED

- **Multimodal:** Image descriptions are embedded alongside text chunks
- **Batch processing:** Chunks are batched in groups of 100 for efficiency
- **Mode-aware storage:** Correct column (`embedding_cloud` vs `embedding_local`) is chosen

### Prompt Construction — IMPROVED

- **Single source of truth** in `prompts.py`
- **Conversation history** is injected for chat mode via `{history_block}`
- **History truncation** at 500 chars per message prevents context explosion

**Remaining issue:** The `history_block` is only included for `chat` mode (line 39 of `chat.py`). This is correct behavior, but the summarize/methodology/etc. modes don't benefit from prior context, which is fine.

### Hallucination Risks — SLIGHTLY REDUCED

The similarity threshold helps, but:
- 0.05 is too low to meaningfully filter hallucination-inducing chunks
- No citation verification (model can still hallucinate page numbers)
- No re-ranking to improve precision of top-K results

### Evaluation Strategy — STILL MISSING

No RAG evaluation of any kind. No retrieval metrics, no answer quality metrics, no benchmark dataset. **This remains the #1 gap for a portfolio project.**

---

## 6. Local Model / Private Mode Review

### Significant Improvement

| Aspect | v1 | v2 |
|--------|----|----|
| Default model | `llama3.2:1b` (far too weak) | `llama3.1:8b` (viable) |
| Embedding model | `all-mpnet-base-v2` (good) | Same (still good) |
| Cloud embedding model | `gemini-embedding-2` | `text-embedding-004` (correct name) |
| Cloud chat model | Inconsistent across files | `gemini-1.5-flash` (consistent) |

### Remaining Issues

1. **Mode capture at upload time** is missing — `ingest_pdf` reads `settings.ai_mode` at execution time, not at upload time. If the user uploads in "hybrid" mode but switches to "cloud" before background ingestion completes, embeddings go to the wrong column.

2. **Paper `ai_mode` column** is written in `init.sql` (line 7) but never set during upload. `crud_papers.py` reads it (`WHERE ai_mode = %s`), but `papers.py` inserts without setting it. This means all papers get `DEFAULT 'local'` regardless of actual mode.

---

## 7. Security and Privacy Review

### Improved

| Issue | Status |
|-------|--------|
| Real keys in `.env.example` | ✅ Fixed |
| No `.gitignore` | ✅ Fixed |
| Real keys in git history | ✅ No commits exist (clean slate) |

### Still Present

| Issue | Severity | Details |
|-------|----------|---------|
| CORS `allow_origins=["*"]` | Medium | Any website can call your API |
| No upload size limit | Medium | OOM crash possible |
| Debug endpoint `/test-ingest` | High | Exposes tracebacks, forces mode change, no auth |
| `OPENAI_API_KEY` in `.env` | Low | Unused, confusing |
| No authentication | Medium | Anyone on the network can access everything |
| Path traversal in image storage | Low | `img_filepath` constructed from PDF content, but uses UUID so risk is minimal |

---

## 8. Code Quality Review

### Folder Organization — GREATLY IMPROVED

| Aspect | v1 Rating | v2 Rating | Notes |
|--------|-----------|-----------|-------|
| Top-level structure | Good | Good | Same |
| Backend structure | Weak (god module) | Strong | Clean separation of concerns |
| API layer | Empty `api/` dir | Good | 3 focused routers |
| LLM module | Good | Better | Prompts extracted |
| RAG module | Weak | Good | Split into ingest + retrieval |
| CRUD layer | N/A (mixed in pipeline) | Good | Dedicated CRUD modules |
| DB layer | Basic | Good | Pool + migrations |
| Frontend | Flat | Flat | Unchanged, acceptable for project size |

### Naming — GOOD

Function names are descriptive and consistent: `ingest_pdf`, `retrieve_context`, `get_recent_history`, `generate_image_description`, `get_chat_provider`.

### Duplication — MOSTLY ELIMINATED

- ✅ Prompt duplication eliminated
- ⚠️ `vector_to_sql()` still duplicated between `ingest.py` and `retrieval.py`
- ⚠️ Citation chip HTML still duplicated in `app.js` (lines 366–377 and 502–514)

### Error Handling — IMPROVED

- `BackgroundTasks` prevents upload timeouts
- `ConnectionPool` has a graceful fallback
- Chat endpoint catches `ValueError` from retrieval and returns user-friendly messages
- Vision module catches all exceptions and returns fallback text

**Remaining gap:** `ingest_pdf` runs in background — if it fails, there's no way for the user to know. The paper appears in the list but has no chunks. Need a status field on the `papers` table (e.g., `status: pending/processing/ready/failed`).

### Type Hints — GOOD

All functions have return type annotations. Parameters are typed. `list[dict]`, `list[float]`, `Optional[str]` used consistently.

### Async/Sync — FIXED

The main v1 issue (async endpoint calling sync `ingest_pdf`) is solved via `BackgroundTasks`. The sync endpoints (`def chat_endpoint`) are correctly handled by FastAPI's threadpool.

### Config Management — IMPROVED

`config.py` is well-organized with clear sections for cloud/local settings. `extra="ignore"` prevents crashes from unused env vars.

**Remaining:** `settings.ai_mode` mutation is still not thread-safe (see Problem 6).

### Testability — IMPROVED BUT INCOMPLETE

The new modular structure is much more testable:
- `chunker.py` is a pure function (easy to test)
- `prompts.py` is a pure function (easy to test)
- Providers can be mocked via the abstract base class
- CRUD functions accept simple parameters

**But:** No actual tests exist. The 20 `test_db*.py` files are debug scripts, not tests.

---

## 9. Missing Features

| Feature | Priority | Status Since v1 | Notes |
|---------|----------|----------------|-------|
| ~~Prompt deduplication~~ | ~~Must Fix~~ | ✅ Done | |
| ~~Background processing~~ | ~~Must Fix~~ | ✅ Done | |
| ~~Connection pooling~~ | ~~Must Fix~~ | ✅ Done | |
| ~~Conversation history~~ | ~~Must Fix~~ | ✅ Done | |
| ~~Similarity threshold~~ | ~~Must Fix~~ | ✅ Done | |
| ~~Better chunking~~ | ~~Must Fix~~ | ✅ Done | |
| ~~API routers~~ | ~~Must Fix~~ | ✅ Done | |
| ~~Vision integration~~ | ~~Must Fix~~ | ✅ Done | |
| Real test suite (pytest) | High | ❌ Missing | Debug scripts are not tests |
| RAG evaluation | High | ❌ Missing | Biggest portfolio gap |
| Upload progress/status | High | ❌ Missing | No way to know if background ingestion succeeded |
| Paper ingestion status field | High | ❌ Missing | `pending/processing/ready/failed` |
| Raise similarity threshold | Medium | ⚠️ Partial | 0.05 is too low |
| Hybrid search (BM25 + vector) | Medium | ❌ Missing | Would significantly improve retrieval |
| Document metadata (authors, DOI) | Medium | ❌ Missing | |
| Architecture diagram | Low | ❌ Still placeholder | |
| Export chat to Markdown | Low | ❌ Missing | |

---

## 10. Prioritized Roadmap

### Priority 1: Must Fix Now (30 minutes each)

| # | Task | Why |
|---|------|-----|
| 1 | Add `psycopg-pool` to `requirements.txt` | Clean install will crash without it |
| 2 | Remove `/test-ingest` endpoint | Security risk in production |
| 3 | Delete all `test_db*.py` debug scripts | Professional appearance |
| 4 | Add `__init__.py` to `app/`, `core/`, `llm/`, `rag/` | Python packaging correctness |
| 5 | Fix CORS to specific origins | Security |
| 6 | Add upload file size limit (100MB) | Prevent OOM crashes |
| 7 | Move `vector_to_sql()` to shared module | Eliminate last duplication |
| 8 | Make first git commit | Preserve your work |

### Priority 2: Important Improvements (1-2 hours each)

| # | Task | Impact |
|---|------|--------|
| 9 | Add `status` field to papers table (`pending/processing/ready/failed`) | Users know if ingestion succeeded |
| 10 | Capture `ai_mode` at upload time, pass to `ingest_pdf` | Prevent mode-switch race condition |
| 11 | Set `papers.ai_mode` during INSERT in `papers.py` | Fix paper filtering (currently all papers get `'local'`) |
| 12 | Raise similarity threshold to 0.2–0.3 | Better hallucination prevention |
| 13 | Write 5 pytest tests: chunker, prompts, retrieval SQL, CRUD, factory | Foundation for test coverage |
| 14 | Remove `OPENAI_API_KEY` from `.env` | Clean up unused variables |
| 15 | Fix chunker overlap logic (use `rfind` instead of `find`) | Better overlap boundaries |
| 16 | Replace `docs/architecture.md` with real Mermaid diagram | Portfolio presentation |

### Priority 3: Advanced Features (2-4 hours each)

| # | Task | Wow Factor |
|---|------|-----------|
| 17 | Build a RAG evaluation script (10 Q&A pairs + retrieval metrics) | Proves the system works |
| 18 | Add hybrid search (BM25 via PostgreSQL `tsvector` + vector) | Production-grade retrieval |
| 19 | Add cross-encoder re-ranking | Precision improvement |
| 20 | Add OCR fallback for scanned PDFs | Broader PDF support |
| 21 | Add table extraction (tabula-py) | Research paper completeness |
| 22 | Add ingestion WebSocket for real-time progress | Premium UX |

---

## 11. Concrete Next Actions

- [ ] **1.** Add `psycopg-pool==3.1.7` to `requirements.txt` under the Database section.

- [ ] **2.** Delete the `/test-ingest` endpoint from `main.py` (lines 83–97).

- [ ] **3.** Delete all 20 `test_db*.py`, `test_extract.py`, `test_ingest.py`, `test_pdf.py`, `test_upload.py` files from `backend/`.

- [ ] **4.** Create empty `__init__.py` in `backend/app/`, `backend/app/core/`, `backend/app/llm/`, `backend/app/rag/`.

- [ ] **5.** Fix CORS in `main.py`: `allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"]`.

- [ ] **6.** Add file size validation in `papers.py` upload endpoint: reject files > 100MB.

- [ ] **7.** Move `vector_to_sql()` from `ingest.py` and `retrieval.py` to `app/db.py` or a new `app/utils.py`.

- [ ] **8.** Run `git add -A && git commit -m "Initial commit: AI Research Assistant with RAG pipeline"`.

- [ ] **9.** Add `status` column to `papers` table (`TEXT DEFAULT 'pending'`), update it to `'ready'` after successful ingestion and `'failed'` on error in `ingest_pdf`.

- [ ] **10.** Create `backend/tests/test_chunker.py` with pytest — test empty input, single paragraph, multi-paragraph, sentence splitting, overlap behavior.

---

## 12. Final Honest Criticism

### Is This Project Portfolio-Worthy Now?

**Almost.** It was "partially worthy" before. Now it is "worthy with minor cleanup."

The codebase demonstrates real software engineering: clean module separation, provider abstraction, proper API structure, background processing, connection pooling, semantic chunking. These are the things an interviewer checks for.

**What's still missing for "impressive":**
1. The debug scripts (`test_db*.py`) need to be deleted — they undermine the professional appearance
2. The `/test-ingest` debug endpoint needs removal
3. The `psycopg-pool` dependency needs to be in requirements
4. You need at least 5 real tests (pytest)
5. You need at least a simple RAG evaluation

### What Would Make It Impressive?

1. **RAG evaluation** (still the #1 differentiator — 10 Q&A pairs, retrieval precision, answer faithfulness). This is what separates "I built a chatbot" from "I built a system I can measure."
2. **Real tests** with pytest and mocking. 5 good tests > 20 debug scripts.
3. **Git history** showing the refactoring journey. An interviewer loves to see a clean commit history: "initial prototype" → "extracted prompts" → "added connection pooling" → "added evaluation."
4. **Architecture diagram** in `docs/` that matches the actual code.
5. **Live demo** — upload a paper, ask a question, show streaming answer with citations, click citation to see PDF. This demo flow is already working.

### What Is Different From v1?

The gap closed significantly. In v1, the gap was "2–3 focused weeks." Now the gap is **2–3 focused days** of cleanup (items 1–8 above) plus **1 focused week** of adding evaluation and tests.

### What Is the Smartest Next Step?

**Cleanup first (30 minutes): items 1–8.** Delete debug scripts, fix missing dependency, fix CORS, make first commit.

**Then tests (2 hours):** Write 5 pytest tests for the chunker, prompts, and factory. This is the highest-impact activity per hour.

**Then evaluation (4 hours):** Create a benchmark with 10 questions about a known paper, measure retrieval precision and answer relevance. Put the results in your README.

---

> **Summary verdict (v2):** The project underwent a genuine and impressive refactoring. The architecture is now clean, modular, and demonstrates real engineering maturity. The remaining issues are minor cleanup (debug scripts, missing dependency, CORS) and portfolio polish (tests, evaluation, git history). You are approximately **one focused weekend** away from a project that would hold up well in an AI Engineer interview. The hardest architectural work is already done.
