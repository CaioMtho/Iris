import os
import httpx

MODEL_SERVER = os.getenv("MODEL_SERVER_URL", "http://ollama:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:3b")
DEFAULT_TIMEOUT = 60.0

async def generate_from_ollama(prompt: str, max_tokens: int = 512, temperature: float = 0.0):
    """
    Chama o endpoint /api/generate do Ollama.
    """
    url = f"{MODEL_SERVER}/api/generate"
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False
    }
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    if isinstance(data, dict) and "choices" in data:
        out = ""
        for c in data.get("choices", []):
            for item in c.get("content", []):
                if item.get("type") == "output_text":
                    out += item.get("text", "")
        if out:
            return out
    return data.get("text") or str(data)
