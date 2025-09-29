import os
import httpx
import logging
import asyncio
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

MODEL_SERVER = os.getenv("MODEL_SERVER_URL", "http://ollama:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:3b")
DEFAULT_TIMEOUT = 180.0
MAX_RETRIES = 3
RETRY_DELAY = 2.0

async def generate_from_ollama(prompt: str, session_id: str, user_name: str = "anonymous",
                               max_tokens: int = 600, temperature: float = 0.15) -> str:
    """
    Cliente Ollama otimizado para prompts estruturados e respostas detalhadas
    """
    
    url = f"{MODEL_SERVER}/api/generate"
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": 0.9 if temperature > 0.2 else 0.8,
            "top_k": 50 if temperature > 0.2 else 30, 
            "repeat_penalty": 1.1,
            "stop": [
                "USUÁRIO:", "USER:", "\n\nUSUÁRIO:", "PERGUNTA:", 
                "\n---\n", "SISTEMA:", "INSTRUCTION:", "FONTES:",
                "\n\nFONTES:", "\n\nPERGUNTA:"
            ],
            "num_ctx": 2500,
            "num_thread": -1,
            "num_keep": 10,
            "presence_penalty": 0.1, 
            "frequency_penalty": 0.1
        }
    }
    
    last_error = None
    start_time = asyncio.get_event_loop().time()
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Ollama attempt {attempt + 1}/{MAX_RETRIES} - Session: {session_id[:8]}... - Tokens: {max_tokens}")
            
            current_timeout = DEFAULT_TIMEOUT - (attempt * 20)  # Reduz timeout nas tentativas
            timeout = httpx.Timeout(current_timeout, connect=15.0, read=current_timeout)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                if "response" in data and data["response"]:
                    generated_text = data["response"].strip()
                    
                    generated_text = _clean_and_validate_response(generated_text)
                    
                    if _is_valid_response(generated_text, prompt):
                        elapsed = asyncio.get_event_loop().time() - start_time
                        logger.info(f"Ollama success in {elapsed:.1f}s - {len(generated_text)} chars - Quality: OK")
                        return generated_text
                    else:
                        logger.warning(f"Response quality low, retrying... (attempt {attempt + 1})")
                        if attempt == MAX_RETRIES - 1:
                            return generated_text 
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    
                else:
                    logger.error(f"Empty response from Ollama: {data}")
                    if attempt == MAX_RETRIES - 1:
                        return "Não consegui gerar uma resposta adequada. Tente reformular sua pergunta."
                    
        except httpx.TimeoutException as e:
            last_error = e
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.warning(f"Timeout após {elapsed:.1f}s - Tentativa {attempt + 1}/{MAX_RETRIES}")
            
            if attempt == MAX_RETRIES - 1:
                return "O modelo está demorando muito para responder. Tente uma pergunta mais específica."
            
            await asyncio.sleep(RETRY_DELAY)
                
        except httpx.HTTPStatusError as e:
            last_error = e
            logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
            
            if e.response.status_code == 404:
                return f"Modelo {MODEL_NAME} não encontrado. Verifique a instalação do Ollama."
            elif e.response.status_code == 500:
                if attempt == MAX_RETRIES - 1:
                    return "Servidor do modelo sobrecarregado. Tente novamente em alguns minutos."
                await asyncio.sleep(RETRY_DELAY * 2)
            elif e.response.status_code == 413:
                if max_tokens > 300:
                    payload["options"]["num_predict"] = max_tokens // 2
                    logger.info(f"Reduzindo tokens para {payload['options']['num_predict']} devido ao erro 413")
                    continue
                else:
                    return "Consulta muito complexa. Tente simplificar sua pergunta."
            else:
                if attempt == MAX_RETRIES - 1:
                    return "Erro de comunicação com o modelo. Tente novamente."
                await asyncio.sleep(RETRY_DELAY)
                    
        except Exception as e:
            last_error = e
            logger.error(f"Unexpected error: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                return "Erro interno do sistema. Contate o suporte se persistir."
            await asyncio.sleep(RETRY_DELAY)
    
    logger.error(f"All attempts failed for session {session_id}: {str(last_error)}")
    return "Sistema temporariamente indisponível. Tente reformular sua pergunta."

def _clean_and_validate_response(text: str) -> str:
    """Limpeza avançada e validação da resposta"""
    if not text:
        return text
    
    prompt_leaks = [
        'SISTEMA:', 'FONTES:', 'INSTRUÇÃO:', 'RESPOSTA:', 'PERGUNTA:',
        'USER:', 'USUÁRIO:', 'ASSISTANT:', 'AI:', 'BOT:',
        'TIPO:', 'TÍTULO:', 'DADOS:', 'CONTEXTO:', 'REGRAS:'
    ]
    
    for leak in prompt_leaks:
        text = text.replace(f'\n{leak}', '\n').replace(f'{leak}', '')
    
    text = text.replace('\n\n\n\n', '\n\n').replace('\n\n\n', '\n\n')
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned_line = ' '.join(line.split())
        if cleaned_line: 
            cleaned_lines.append(cleaned_line)
        elif cleaned_lines and cleaned_lines[-1]:
            cleaned_lines.append('')
    
    result = '\n'.join(cleaned_lines)
    
    sentences = result.split('.')
    filtered_sentences = []
    last_sentence = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and sentence != last_sentence:
            filtered_sentences.append(sentence)
            last_sentence = sentence
    
    if filtered_sentences:
        result = '. '.join(filtered_sentences)
        if not result.endswith('.'):
            result += '.'
    
    return result.strip()

def _is_valid_response(response: str, prompt: str) -> bool:
    """Valida se a resposta tem qualidade mínima"""
    if not response or len(response.strip()) < 30:
        return False
    
    response_clean = response.lower().replace('\n', ' ')
    prompt_clean = prompt.lower().replace('\n', ' ')
    
    if len(set(response_clean.split()) - set(prompt_clean.split())) < 5:
        return False
    
    political_indicators = [
        'deputado', 'projeto', 'votou', 'partido', 'votação', 'câmara',
        'sim', 'não', 'favor', 'contra', 'aprovado', 'política', 'vereador'
    ]
    
    found_indicators = sum(1 for indicator in political_indicators if indicator in response.lower())
    
    return found_indicators >= 1