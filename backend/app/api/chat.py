from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json
from pathlib import Path
from app.core.config import settings
from app.rag.retrieval import retrieve_context
from app.crud_sessions import save_chat_to_db, get_recent_history
from app.llm.factory import get_chat_provider

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    session_id: int
    question: Optional[str] = None
    top_k: int = 5
    paper_ids: Optional[List[int]] = None
    mode: str = "chat"

@router.post("")
def chat_endpoint(req: ChatRequest):
    question = req.question
    if req.mode != "chat" and not question:
        question = "summary methodology contributions limitations literature review future work gaps findings"
        req.top_k = 10 

    try:
        contexts = retrieve_context(question, top_k=req.top_k, paper_ids=req.paper_ids)
    except ValueError as e:
        return {"answer": str(e), "sources": []}

    if not contexts:
        return {
            "answer": f"No relevant chunks were found for this AI mode. Make sure you have uploaded the paper while '{settings.ai_mode.upper()}' mode was active, or try rephrasing your question.",
            "sources": [],
        }

    history = get_recent_history(req.session_id) if req.mode == "chat" else ""

    chat_provider = get_chat_provider()
    answer = chat_provider.generate_answer(question, contexts, mode=req.mode, history=history)

    sources = [
        {
            "paper_title": ctx["paper_title"],
            "page_number": ctx["page_number"],
            "similarity": round(ctx["similarity"], 4),
            "content": ctx["content"],
            "image_path": str(Path(ctx["image_path"]).name) if ctx.get("image_path") else None,
        }
        for ctx in contexts
    ]

    save_chat_to_db(req.session_id, req.question, answer, sources, req.mode)
    return {"answer": answer, "sources": sources}

@router.post("/stream")
def chat_stream_endpoint(req: ChatRequest):
    def generator():
        question = req.question
        if req.mode != "chat" and not question:
            question = "summary methodology contributions limitations literature review future work gaps findings"
            req.top_k = 10 

        try:
            contexts = retrieve_context(question, top_k=req.top_k, paper_ids=req.paper_ids)
        except ValueError as e:
            yield json.dumps({"type": "sources", "data": []}) + "\n"
            yield json.dumps({"type": "token", "data": f"**Error:** {str(e)}"}) + "\n"
            return

        if not contexts:
            error_msg = f"No relevant chunks were found for this AI mode. Make sure you have uploaded the paper while '{settings.ai_mode.upper()}' mode was active, or try rephrasing your question."
            yield json.dumps({"type": "sources", "data": []}) + "\n"
            yield json.dumps({"type": "token", "data": error_msg}) + "\n"
            return

        sources = [
            {
                "paper_title": ctx["paper_title"],
                "page_number": ctx["page_number"],
                "similarity": round(ctx["similarity"], 4),
                "content": ctx["content"],
                "image_path": str(Path(ctx["image_path"]).name) if ctx.get("image_path") else None,
            }
            for ctx in contexts
        ]

        yield json.dumps({"type": "sources", "data": sources}) + "\n"

        history = get_recent_history(req.session_id) if req.mode == "chat" else ""
        chat_provider = get_chat_provider()
        gen = chat_provider.generate_answer_stream(question, contexts, mode=req.mode, history=history)

        full_answer = ""
        for token in gen:
            full_answer += token
            yield json.dumps({"type": "token", "data": token}) + "\n"

        save_chat_to_db(req.session_id, req.question, full_answer, sources, req.mode)

    return StreamingResponse(generator(), media_type="application/x-ndjson")

