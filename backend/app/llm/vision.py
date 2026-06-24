import base64
from app.core.config import settings
from google import genai
import httpx
import logging

logger = logging.getLogger(__name__)

def generate_image_description(image_path: str, mode: str) -> str:
    prompt = "Please describe this chart, graph, or image in detail. Extract any relevant data, axes, trends, or text visible. If it is a diagram, explain the flow."
    
    try:
        if mode.lower() == "private":
            # Use local Moondream via Ollama
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            
            payload = {
                "model": "moondream",
                "prompt": prompt,
                "images": [img_b64],
                "stream": False
            }
            logger.info(f"Generating local description with moondream for {image_path}")
            response = httpx.post(f"{settings.ollama_base_url}/api/generate", json=payload, timeout=120.0)
            response.raise_for_status()
            return response.json().get("response", "")
        else:
            # Use Cloud Gemini
            logger.info(f"Generating cloud description with Gemini for {image_path}")
            client = genai.Client(api_key=settings.gemini_api_key)
            
            # Use PIL to load the image
            from PIL import Image
            img = Image.open(image_path)
            
            response = client.models.generate_content(
                model="gemini-2.5-flash", # Use standard vision capable model
                contents=[img, prompt]
            )
            return response.text
            
    except Exception as e:
        logger.error(f"Failed to generate image description for {image_path}: {e}")
        return "Image description generation failed."
