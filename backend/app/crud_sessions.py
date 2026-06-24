from app.db import get_connection
from app.core.config import settings
import json

def create_session() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO sessions (title) VALUES ('New Chat') RETURNING id")
            return cur.fetchone()[0]

def get_sessions() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC")
            rows = cur.fetchall()
            
    return [{"id": row[0], "title": row[1], "created_at": str(row[2])} for row in rows]

def get_session_chat(session_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, content, sources 
                FROM chat_logs 
                WHERE session_id = %s AND role IS NOT NULL
                ORDER BY id ASC
                """,
                (session_id,)
            )
            rows = cur.fetchall()
            
    messages = []
    for row in rows:
        messages.append({
            "role": row[0],
            "content": row[1],
            "sources": row[2] if row[2] else []
        })
    return messages

def get_recent_history(session_id: int, limit: int = 5) -> str:
    messages = get_session_chat(session_id)
    if not messages:
        return ""
    
    recent = messages[-limit:]
    history_str = "--- Previous Conversation History ---\n"
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        # truncate long assistant answers
        content = msg["content"]
        if len(content) > 500:
            content = content[:500] + "... [truncated]"
        history_str += f"{role}: {content}\n\n"
    history_str += "--------------------------------------\n"
    return history_str

def update_session(session_id: int, title: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE sessions SET title = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (title, session_id))
            return cur.rowcount > 0

def delete_session(session_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
            return cur.rowcount > 0

def save_chat_to_db(session_id: int, original_question: str, answer: str, sources: list, mode: str):
    model_used = f"local ({settings.local_chat_model})" if settings.ai_mode.lower() == "private" else f"gemini ({mode})"

    with get_connection() as conn:
        with conn.cursor() as cur:
            if original_question:
                cur.execute(
                    "INSERT INTO chat_logs (session_id, role, content) VALUES (%s, 'user', %s)",
                    (session_id, original_question)
                )
            elif mode != "chat":
                mode_name = mode.replace('_', ' ').title()
                cur.execute(
                    "INSERT INTO chat_logs (session_id, role, content) VALUES (%s, 'user', %s)",
                    (session_id, f"*[Ran {mode_name} on selected papers]*")
                )
            
            sources_json = json.dumps(sources)
            cur.execute(
                """
                INSERT INTO chat_logs (session_id, role, content, sources, model_used) 
                VALUES (%s, 'assistant', %s, %s::jsonb, %s)
                """,
                (session_id, answer, sources_json, model_used)
            )
            
            if original_question:
                cur.execute("SELECT title FROM sessions WHERE id = %s", (session_id,))
                title = cur.fetchone()[0]
                if title == "New Chat":
                    new_title = original_question[:50]
                    cur.execute("UPDATE sessions SET title = %s WHERE id = %s", (new_title, session_id))
