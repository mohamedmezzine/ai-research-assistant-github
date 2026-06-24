from abc import ABC, abstractmethod

class ChatProvider(ABC):
    @abstractmethod
    def generate_answer(self, question: str, contexts: list[dict], mode: str = "chat", history: str = "") -> str:
        pass

    @abstractmethod
    def generate_answer_stream(self, question: str, contexts: list[dict], mode: str = "chat", history: str = ""):
        pass

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        pass

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]
