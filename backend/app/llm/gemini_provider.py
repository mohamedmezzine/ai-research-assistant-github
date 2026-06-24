from google import genai
from app.core.config import settings
from app.llm.prompts import get_prompt
from app.llm.base import ChatProvider, EmbeddingProvider

# Initialize Gemini client once
_gemini_client = None

def get_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


class GeminiEmbeddingProvider(EmbeddingProvider):
    def embed_text(self, text: str) -> list[float]:
        client = get_client()
        response = client.models.embed_content(
            model=settings.cloud_embedding_model,
            contents=text,
        )
        return response.embeddings[0].values

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = get_client()
        response = client.models.embed_content(
            model=settings.cloud_embedding_model,
            contents=texts,
        )
        return [emb.values for emb in response.embeddings]


class GeminiChatProvider(ChatProvider):

    def generate_answer(self, question: str, contexts: list[dict], mode: str = "chat", history: str = "") -> str:
        selected_prompt = get_prompt(question, contexts, mode, history)
        
        contents_list = [selected_prompt]
        from PIL import Image
        import os
        for ctx in contexts:
            img_path = ctx.get("image_path")
            if img_path and os.path.exists(img_path):
                try:
                    contents_list.append(Image.open(img_path))
                except Exception:
                    pass
                    
        client = get_client()
        response = client.models.generate_content(
            model=settings.cloud_chat_model,
            contents=contents_list,
        )
        return response.text or "No answer generated."

    def generate_answer_stream(self, question: str, contexts: list[dict], mode: str = "chat", history: str = ""):
        selected_prompt = get_prompt(question, contexts, mode, history)
        
        contents_list = [selected_prompt]
        from PIL import Image
        import os
        for ctx in contexts:
            img_path = ctx.get("image_path")
            if img_path and os.path.exists(img_path):
                try:
                    contents_list.append(Image.open(img_path))
                except Exception:
                    pass
                    
        client = get_client()
        response = client.models.generate_content_stream(
            model=settings.cloud_chat_model,
            contents=contents_list,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
