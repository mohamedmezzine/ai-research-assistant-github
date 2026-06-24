from pathlib import Path
import fitz  # PyMuPDF
import os
import uuid

def extract_pdf_pages(file_path: str) -> list[dict]:
    """Extract text and images from a PDF page by page."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    # Create images directory
    # If file_path is like ../data/papers/file.pdf, images should go to ../data/images/
    images_dir = path.parent.parent / "images"
    os.makedirs(images_dir, exist_ok=True)

    pages = []
    with fitz.open(file_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            
            images = []
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Minimum size to ignore tiny icons/lines
                if len(image_bytes) < 5000:
                    continue
                
                img_filename = f"{path.stem}_p{page_index}_i{img_index}_{uuid.uuid4().hex[:6]}.{image_ext}"
                img_filepath = images_dir / img_filename
                
                with open(img_filepath, "wb") as f:
                    f.write(image_bytes)
                
                # Store relative path so frontend can request it via /images/
                images.append(str(img_filepath))

            if text or images:
                pages.append({"page_number": page_index, "text": text, "images": images})
    return pages
