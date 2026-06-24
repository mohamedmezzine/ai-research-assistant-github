from app.db import get_connection
from app.llm.factory import get_embedding_provider
from app.core.config import settings

def vector_to_sql(vector: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vector) + "]"

def retrieve_context(question: str, top_k: int = 5, paper_ids: list[int] = None) -> list[dict]:
    # Check if papers exist first
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM papers LIMIT 1")
            if not cur.fetchone():
                raise ValueError("No papers uploaded. Please upload a PDF to your Knowledge Base first.")

    if paper_ids is not None and len(paper_ids) == 0:
        raise ValueError("No papers selected. Please check at least one paper from your Knowledge Base.")

    embedding_provider = get_embedding_provider()
    question_embedding = vector_to_sql(embedding_provider.embed_text(question))
    
    active_mode = settings.ai_mode.lower()
    target_column = "embedding_cloud" if active_mode == "cloud" else "embedding_local"

    query = f"""
        SELECT chunk_id, paper_title, page_number, content, image_path, similarity
        FROM (
            SELECT
                chunks.id AS chunk_id,
                papers.title AS paper_title,
                chunks.page_number,
                chunks.content,
                chunks.image_path,
                1 - (chunks.{target_column} <=> %s::vector) AS similarity
            FROM chunks
            JOIN papers ON papers.id = chunks.paper_id
            WHERE chunks.{target_column} IS NOT NULL
    """
    
    params = [question_embedding]
    
    if paper_ids:
        query += " AND papers.id = ANY(%s)"
        params.append(paper_ids)
        
    query += f"""
        ) AS sim_query
        WHERE similarity > 0.05
        ORDER BY similarity DESC
        LIMIT %s
    """
    params.append(top_k)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

    return [
        {
            "chunk_id": row[0],
            "paper_title": row[1],
            "page_number": row[2],
            "content": row[3],
            "image_path": row[4],
            "similarity": float(row[5]),
        }
        for row in rows
    ]
