from app.core.config import settings
from app.llm.base import EmbeddingProvider
from sentence_transformers import SentenceTransformer
import torch

# Load model lazily
_model = None

def get_model():
    global _model
    if _model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = SentenceTransformer(settings.local_embedding_model, device=device)
    return _model

class LocalEmbeddingProvider(EmbeddingProvider):
    def embed_text(self, text: str) -> list[float]:
        model = get_model()
        embedding = model.encode(text)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = get_model()
        embeddings = model.encode(texts)
        return embeddings.tolist()
