from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.crud_sessions import get_sessions, get_session_chat, create_session, delete_session, update_session

router = APIRouter(prefix="/sessions", tags=["sessions"])

class SessionTitleUpdate(BaseModel):
    title: str

@router.get("")
def list_sessions():
    return get_sessions()

@router.post("")
def new_session():
    session_id = create_session()
    return {"id": session_id, "title": "New Chat"}

@router.get("/{session_id}/chat")
def get_chat_history(session_id: int):
    return get_session_chat(session_id)

@router.put("/{session_id}")
def edit_session(session_id: int, request: SessionTitleUpdate):
    success = update_session(session_id, request.title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session updated"}

@router.delete("/{session_id}")
def remove_session(session_id: int):
    success = delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}
