import httpx
import json
from app.core.config import settings
from app.llm.prompts import get_prompt
from app.llm.base import ChatProvider

class OllamaChatProvider(ChatProvider):


    def generate_answer(self, question: str, contexts: list[dict], mode: str = "chat", history: str = "") -> str:
        selected_prompt = get_prompt(question, contexts, mode, history)

        payload = {
            "model": settings.local_chat_model,
            "prompt": selected_prompt,
            "stream": False
        }

        url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "No answer generated.")
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to Ollama server at {url}. Ensure Ollama is running. Error: {e}")
        except Exception as e:
            raise Exception(f"Local AI Error: {e}")

    def generate_answer_stream(self, question: str, contexts: list[dict], mode: str = "chat", history: str = ""):
        selected_prompt = get_prompt(question, contexts, mode, history)

        payload = {
            "model": settings.local_chat_model,
            "prompt": selected_prompt,
            "stream": True
        }

        url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"

        try:
            with httpx.Client(timeout=120.0) as client:
                with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line:
                            data = json.loads(line)
                            yield data.get("response", "")
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to Ollama server at {url}. Ensure Ollama is running. Error: {e}")
        except Exception as e:
            raise Exception(f"Local AI Error: {e}")
