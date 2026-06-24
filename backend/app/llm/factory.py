from app.core.config import settings
from app.llm.base import ChatProvider, EmbeddingProvider
from app.llm.gemini_provider import GeminiChatProvider, GeminiEmbeddingProvider
from app.llm.ollama_provider import OllamaChatProvider

_chat_providers = {
    "gemini": GeminiChatProvider,
    "ollama": OllamaChatProvider,
}

_embedding_providers = {
    "gemini": GeminiEmbeddingProvider,
}

def _get_local_embedding_provider_class():
    try:
        from app.llm.local_embeddings import LocalEmbeddingProvider
    except ImportError as exc:
        raise RuntimeError(
            "Local embeddings require optional dependencies. Install "
            "sentence-transformers and torch, or switch AI_MODE to cloud."
        ) from exc
    return LocalEmbeddingProvider

def get_chat_provider() -> ChatProvider:
    mode = settings.ai_mode.lower()
    
    if mode == "private":
        provider_name = settings.local_chat_provider
    elif mode == "hybrid":
        # Hybrid uses local embeddings but cloud chat
        provider_name = settings.cloud_chat_provider
    else:
        # Default to cloud
        provider_name = settings.cloud_chat_provider
        
    provider_class = _chat_providers.get(provider_name, GeminiChatProvider)
    return provider_class()

def get_embedding_provider() -> EmbeddingProvider:
    mode = settings.ai_mode.lower()
    
    if mode == "private" or mode == "hybrid":
        provider_name = settings.local_embedding_provider
    else:
        # Default to cloud
        provider_name = settings.cloud_embedding_provider

    if provider_name == "sentence_transformers":
        provider_class = _get_local_embedding_provider_class()
    else:
        provider_class = _embedding_providers.get(provider_name, GeminiEmbeddingProvider)
    return provider_class()
