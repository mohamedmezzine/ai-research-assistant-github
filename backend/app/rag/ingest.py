from app.db import get_connection
from app.rag.pdf_loader import extract_pdf_pages
from app.rag.chunker import chunk_text
from app.llm.factory import get_embedding_provider
from app.core.config import settings
from app.llm.vision import generate_image_description
import logging

logger = logging.getLogger(__name__)

def vector_to_sql(vector: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vector) + "]"

def ingest_pdf(file_path: str, title: str, paper_id: int) -> dict:
    logger.info(f"Ingesting PDF: {title} (ID: {paper_id})")
    pages = extract_pdf_pages(file_path)

    if not pages:
        raise ValueError("No extractable text found in this PDF.")

    embedding_provider = get_embedding_provider()
    active_mode = settings.ai_mode.lower()

    with get_connection() as conn:
        with conn.cursor() as cur:
            total_chunks = 0
            all_chunks_info = []

            for page in pages:
                # Text
                if page.get("text"):
                    chunks = chunk_text(page["text"])
                    for chunk in chunks:
                        all_chunks_info.append({"page_number": page["page_number"], "content": chunk, "image_path": None})
                
                # Images
                if page.get("images"):
                    for img_path in page["images"]:
                        description = generate_image_description(img_path, active_mode)
                        if description:
                            chunk_content = f"[IMAGE] Description: {description}"
                            all_chunks_info.append({"page_number": page["page_number"], "content": chunk_content, "image_path": img_path})

            if all_chunks_info:
                texts_to_embed = [item["content"] for item in all_chunks_info]
                
                batch_size = 100
                all_embeddings = []
                for i in range(0, len(texts_to_embed), batch_size):
                    batch_texts = texts_to_embed[i:i+batch_size]
                    batch_embeddings = embedding_provider.embed_batch(batch_texts)
                    all_embeddings.extend(batch_embeddings)
                
                for info, embedding_vector in zip(all_chunks_info, all_embeddings):
                    embedding_sql = vector_to_sql(embedding_vector)
                    
                    if active_mode == "cloud":
                        cur.execute(
                            """
                            INSERT INTO chunks (paper_id, page_number, content, image_path, embedding_cloud)
                            VALUES (%s, %s, %s, %s, %s::vector)
                            """,
                            (paper_id, info["page_number"], info["content"], info["image_path"], embedding_sql),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO chunks (paper_id, page_number, content, image_path, embedding_local)
                            VALUES (%s, %s, %s, %s, %s::vector)
                            """,
                            (paper_id, info["page_number"], info["content"], info["image_path"], embedding_sql),
                        )
                    total_chunks += 1

    return {"id": paper_id, "title": title, "pages": len(pages), "chunks": total_chunks}

