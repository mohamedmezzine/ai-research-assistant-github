from app.db import get_connection
from app.core.config import settings

def get_all_papers() -> list[dict]:
    active_mode = "cloud" if settings.ai_mode.lower() == "cloud" else "local"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, created_at FROM papers WHERE ai_mode = %s ORDER BY created_at DESC", (active_mode,))
            rows = cur.fetchall()
            
    return [{"id": row[0], "title": row[1], "created_at": str(row[2])} for row in rows]

def delete_paper(paper_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM papers WHERE id = %s", (paper_id,))
            return cur.rowcount > 0

