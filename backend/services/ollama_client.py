import os
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

MODEL_SERVER = os.getenv("MODEL_SERVER_URL", "http://ollama:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:3b")
DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 3

async def generate_from_ollama(prompt: str, session_id: str, user_name: str = "anonymous",
                               max_tokens: int = 512, temperature: float = 0.2) -> str:
    """
    Usa a API oficial do Ollama (/api/generate) com retry logic e error handling.
    """
    url = f"{MODEL_SERVER}/api/generate"
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "stop": ["USUÁRIO:", "USER:", "\n\nUSUÁRIO:", "\n\nASSISTENTE:"]
        }
    }
    
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                if "response" in data:
                    return data["response"].strip()
                else:
                    logger.error(f"Resposta inesperada do Ollama: {data}")
                    return "Desculpe, ocorreu um erro interno. Tente novamente."
                    
        except httpx.TimeoutException as e:
            last_error = e
            logger.warning(f"Timeout na tentativa {attempt + 1}/{MAX_RETRIES}")
            if attempt == MAX_RETRIES - 1:
                return "Desculpe, o sistema está demorando para responder. Tente novamente em alguns instantes."
                
        except httpx.HTTPStatusError as e:
            last_error = e
            logger.error(f"Erro HTTP {e.response.status_code}: {e.response.text}")
            if e.response.status_code == 404:
                return f"Modelo {MODEL_NAME} não encontrado. Verifique se está instalado no Ollama."
            elif attempt == MAX_RETRIES - 1:
                return "Desculpe, ocorreu um erro no servidor. Tente novamente mais tarde."
                
        except Exception as e:
            last_error = e
            logger.error(f"Erro inesperado: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                return "Desculpe, ocorreu um erro interno. Tente novamente."
    
    return "Sistema temporariamente indisponível. Tente novamente."