import re

def chunk_text(text: str, max_chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    """
    Semantically chunk text by trying to split on paragraphs, then sentences, then words.
    """
    # Try to split by double newlines (paragraphs)
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        if len(current_chunk) + len(para) + 2 <= max_chunk_size:
            current_chunk += para + "\n\n"
        else:
            # If current chunk is not empty, save it
            if current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap if possible
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                # Find a good boundary for overlap
                last_period = overlap_text.find('. ')
                if last_period != -1:
                    overlap_text = overlap_text[last_period + 2:]
                current_chunk = overlap_text + "\n\n" if overlap_text else ""
            
            # If a single paragraph is larger than max_chunk_size, we must split it by sentences
            if len(para) > max_chunk_size:
                sentences = re.split(r'(?<=\.)\s+', para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        # If a single sentence is still too long, hard truncate
                        if len(sentence) > max_chunk_size:
                            for i in range(0, len(sentence), max_chunk_size - overlap):
                                chunks.append(sentence[i:i + max_chunk_size])
                            current_chunk = ""
                        else:
                            current_chunk = sentence + " "
            else:
                current_chunk += para + "\n\n"
                
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    return chunks
