# Architecture

```text
User
 |
 v
FastAPI API
 |
 |-- /papers/upload -> PDF extraction -> chunking -> embeddings -> PostgreSQL + pgvector
 |
 |-- /chat -> query embedding -> vector search -> LLM answer -> citations
 |
 v
PostgreSQL + pgvector
```
