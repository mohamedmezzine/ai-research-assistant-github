from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db import run_migrations

from app.api import papers, sessions, chat

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Running database migrations...")
    run_migrations()
    yield

app = FastAPI(title="AI Research Assistant", lifespan=lifespan)

# Update CORS to be more restrictive based on Critic Review
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(papers.router)
app.include_router(sessions.router)
app.include_router(chat.router)

class ModeUpdateRequest(BaseModel):
    mode: str

@app.put("/settings/ai-mode")
def update_mode(request: ModeUpdateRequest):
    valid_modes = ["cloud", "hybrid", "private"]
    if request.mode.lower() not in valid_modes:
        raise HTTPException(status_code=400, detail="Invalid AI mode.")
    settings.ai_mode = request.mode.lower()
    return {"message": f"AI mode set to {settings.ai_mode}"}

@app.get("/settings/ai-mode")
def get_mode():
    return {"mode": settings.ai_mode}

# Static Mounts
app.mount(
    "/files/papers",
    StaticFiles(directory=Path(settings.upload_dir) if Path(settings.upload_dir).is_absolute() else Path(__file__).resolve().parents[1] / settings.upload_dir),
    name="papers"
)

images_dir = Path(settings.upload_dir).parent / "images"
images_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/images",
    StaticFiles(directory=images_dir),
    name="images"
)




from fastapi.responses import FileResponse
frontend_dir = Path(__file__).resolve().parents[2] / "frontend"

@app.get("/")
def serve_frontend():
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"detail": "Frontend not found"}

@app.get("/test-ingest")
def test_ingest():
    try:
        from app.rag.ingest import ingest_pdf
        import os
        from app.core.config import settings
        settings.ai_mode = "hybrid"  # FORCE HYBRID MODE
        pdf_dir = settings.upload_dir
        pdfs = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
        latest_pdf = max(pdfs, key=os.path.getctime)
        res = ingest_pdf(latest_pdf, "Test Paper", 999)
        return {"status": "success", "result": res}
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

app.mount("/", StaticFiles(directory=str(frontend_dir)), name="frontend_static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)



