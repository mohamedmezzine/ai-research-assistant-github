from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
from pathlib import Path
from app.core.config import settings
from app.rag.ingest import ingest_pdf
from app.crud_papers import get_all_papers, delete_paper
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["papers"])

class PaperResponse(BaseModel):
    id: int
    title: str
    created_at: str

@router.get("", response_model=list[PaperResponse])
def list_papers():
    return get_all_papers()

@router.post("/upload")
async def upload_paper(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, file.filename)
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    title = Path(file.filename).stem.replace("_", " ").title()
    
    # Create the paper in the database synchronously so we have an ID to return
    from app.db import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM papers WHERE title = %s", (title,))
            result = cur.fetchone()
            if result:
                paper_id = result[0]
                cur.execute("DELETE FROM chunks WHERE paper_id = %s", (paper_id,))
            else:
                cur.execute(
                    "INSERT INTO papers (title, file_path) VALUES (%s, %s) RETURNING id",
                    (title, file_path),
                )
                paper_id = cur.fetchone()[0]

    # Run heavy chunking and embedding in background
    background_tasks.add_task(ingest_pdf, file_path, title, paper_id)
    
    return {"message": "Paper uploaded and processing started in background", "title": title, "id": paper_id}

@router.delete("/{paper_id}")
def remove_paper(paper_id: int):
    success = delete_paper(paper_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"message": "Paper deleted successfully"}


