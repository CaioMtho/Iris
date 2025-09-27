import uuid
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from backend.db.database import SessionLocal
from backend.models.chat_models import SessionMessage, ResponseLog
from backend.models.models import DocumentoPolitico, Politico
from backend.services.ollama_client import generate_from_ollama
from backend.services.rag_memory import find_documents_for_query as find_docs_memoria

logger = logging.getLogger(__name__)

IRIS_NAME = "Iris"
MAX_HISTORY_MESSAGES = 10  # Número de mensagens, não caracteres
MAX_SNIPPET_CHARS = 600
MAX_CONTEXT_TOKENS = 1500  # Reservar espaço para resposta

def _snippet(text: str, chars: int = MAX_SNIPPET_CHARS) -> str:
    if not text:
        return ""
    s = text.replace("\n", " ").strip()
    return (s[:chars] + "...") if len(s) > chars else s

def get_session_history(session_id: str, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict]:
    """Pega histórico por mensagens completas, não por caracteres"""
    try:
        db = SessionLocal()
        try:
            rows = db.query(SessionMessage)\
                    .filter(SessionMessage.session_id == session_id)\
                    .order_by(SessionMessage.created_at.desc())\
                    .limit(limit * 2).all()  # Pega mais para garantir pares user/assistant
            
            # Organizar em ordem cronológica e garantir pares
            messages = []
            rows.reverse()  # Mais antigo primeiro
            
            for row in rows[-limit:]:  # Pega apenas as últimas mensagens
                messages.append({
                    "role": row.role, 
                    "message": row.message, 
                    "created_at": row.created_at.isoformat()
                })
            
            return messages
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {str(e)}")
        return []

def save_session_message(session_id: str, role: str, message: str):
    try:
        db = SessionLocal()
        try:
            sm = SessionMessage(session_id=session_id, role=role, message=message)
            db.add(sm)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem: {str(e)}")

def log_response(prompt: str, response: str, session_id: Optional[str], user_id: Optional[str], sources: List[str]):
    try:
        db = SessionLocal()
        try:
            rl = ResponseLog(
                session_id=session_id, 
                user_id=user_id, 
                prompt=prompt, 
                response=response, 
                sources=sources
            )
            db.add(rl)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao salvar log: {str(e)}")

def find_documents_for_query(q: str, limit: int = 3) -> List[Dict]:
    """RAG com error handling e busca otimizada"""
    try:
        db = SessionLocal()
        try:
            # Busca mais eficiente com índices
            query_terms = q.lower().split()[:3]  # Limitar termos de busca
            
            base_query = db.query(DocumentoPolitico)
            
            # Buscar por termos individuais (mais eficiente que ILIKE complexo)
            for term in query_terms:
                if len(term) >= 3:  # Ignorar palavras muito pequenas
                    pattern = f"%{term}%"
                    base_query = base_query.filter(
                        (DocumentoPolitico.titulo.ilike(pattern)) |
                        (DocumentoPolitico.resumo_simplificado.ilike(pattern))
                    )
            
            rows = base_query.order_by(DocumentoPolitico.created_at.desc()).limit(limit).all()
            
            docs = []
            for r in rows:
                summary = r.resumo_simplificado or r.ementa or r.titulo or ""
                docs.append({
                    "id_documento_origem": r.id_documento_origem or str(r.id),
                    "titulo": r.titulo,
                    "url_fonte": r.url_fonte,
                    "snippet": _snippet(summary),
                    "tipo": r.tipo
                })
            return docs
            
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro na busca de documentos: {str(e)}")
        return []

def find_politicians_for_query(q: str, limit: int = 2) -> List[Dict]:
    """Busca políticos com error handling"""
    try:
        db = SessionLocal()
        try:
            terms = q.lower().split()[:2]
            base_query = db.query(Politico).filter(Politico.ativo == True)
            
            for term in terms:
                if len(term) >= 3:
                    pattern = f"%{term}%"
                    base_query = base_query.filter(
                        (Politico.nome.ilike(pattern)) |
                        (Politico.partido.ilike(pattern)) |
                        (Politico.uf.ilike(pattern))
                    )
            
            rows = base_query.limit(limit).all()
            
            docs = []
            for r in rows:
                snippet_text = f"Deputado(a) {r.nome}, {r.partido}-{r.uf}"
                if r.ideologia_eco is not None:
                    snippet_text += f". Perfil ideológico disponível."
                
                docs.append({
                    "id_documento_origem": f"politico-{r.id_camara}",
                    "titulo": f"{r.nome} ({r.partido}-{r.uf})",
                    "url_fonte": None,
                    "snippet": _snippet(snippet_text),
                    "tipo": "politico"
                })
            return docs
            
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro na busca de políticos: {str(e)}")
        return []

SYSTEM_PROMPT = f"""Você é {IRIS_NAME}, assistente especializada em política brasileira.

REGRAS IMPORTANTES:
- Use APENAS as informações das fontes fornecidas
- Se não houver informação suficiente, diga: "Não encontrei informações sobre isso nas fontes disponíveis"
- Seja objetiva e factual
- Cite as fontes numeradas quando relevante
- Mantenha respostas concisas (máximo 3 parágrafos)
- Para perguntas sobre deputados, foque em: partido, UF, posicionamentos conhecidos
- Para votações, explique o tema de forma simples

FORMATO DE RESPOSTA:
1. Resposta direta à pergunta
2. Informações complementares das fontes (se houver)
3. Menção às fontes usadas (ex: "Conforme fonte [1]")"""

def build_prompt(chat_history: List[Dict], user_message: str, retrieved_docs: List[Dict]) -> str:
    """Constrói prompt otimizado para Llama 3.2:3b"""
    
    # Histórico mais compacto
    history_text = ""
    if chat_history:
        for m in chat_history[-4:]:  # Apenas últimas 2 interações
            role = "USUÁRIO" if m.get("role") == "user" else "IRIS"
            msg = m.get("message", "")[:200]  # Limitar tamanho
            history_text += f"{role}: {msg}\n"
    
    # Fontes mais estruturadas
    sources_text = ""
    for i, d in enumerate(retrieved_docs[:3], start=1):  # Máximo 3 fontes
        title = d.get("titulo", "")[:100]
        snippet = d.get("snippet", "")[:300]
        doc_type = d.get("tipo", "documento")
        sources_text += f"[{i}] {title} ({doc_type})\n{snippet}\n\n"
    
    # Construir prompt final
    prompt = SYSTEM_PROMPT
    
    if history_text.strip():
        prompt += f"\n\nCONTEXTO DA CONVERSA:\n{history_text}"
    
    if sources_text.strip():
        prompt += f"\n\nFONTES DISPONÍVEIS:\n{sources_text}"
    
    prompt += f"\n\nPERGUNTA: {user_message}\n\nRESPOSTA:"
    
    return prompt

async def handle_chat(user_message: str, session_id: Optional[str] = None, 
                      user_id: Optional[str] = None, max_tokens: int = 400, 
                      temperature: float = 0.2) -> Dict:
    """Handler principal com error handling completo"""
    
    start_time = datetime.now()
    
    try:
        # Validação de entrada
        if not user_message or len(user_message.strip()) < 2:
            return {
                "response": "Por favor, faça uma pergunta sobre política brasileira.",
                "sources": [],
                "session_id": session_id,
                "error": "Entrada inválida"
            }
        
        if len(user_message) > 500:
            user_message = user_message[:500] + "..."
        
        session_id = session_id or str(uuid.uuid4())
        
        # Buscar contexto
        history = get_session_history(session_id)
        
        # RAG híbrido com error handling
        docs_memoria = find_docs_memoria(user_message, limit=2)
        docs_banco = find_documents_for_query(user_message, limit=2)
        docs_politicos = find_politicians_for_query(user_message, limit=2)
        
        retrieved_docs = docs_memoria + docs_banco + docs_politicos
        
        # Construir e executar prompt
        prompt = build_prompt(history, user_message, retrieved_docs)
        
        # Salvar pergunta do usuário
        save_session_message(session_id, "user", user_message)
        
        # Gerar resposta
        response_text = await generate_from_ollama(
            prompt, 
            session_id=session_id, 
            user_name=user_id or "anonymous",
            max_tokens=max_tokens, 
            temperature=temperature
        )
        
        # Salvar resposta
        save_session_message(session_id, "assistant", response_text)
        
        # Log completo
        sources_used = [d.get("id_documento_origem") for d in retrieved_docs if d.get("id_documento_origem")]
        log_response(prompt, response_text, session_id, user_id, sources_used)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "response": response_text,
            "sources": [
                {
                    "id": d.get("id_documento_origem"),
                    "title": d.get("titulo"),
                    "type": d.get("tipo", "documento")
                } 
                for d in retrieved_docs if d.get("id_documento_origem")
            ],
            "session_id": session_id,
            "processing_time": processing_time
        }
        
    except Exception as e:
        logger.error(f"Erro no handle_chat: {str(e)}")
        return {
            "response": "Desculpe, ocorreu um erro interno. Nossa equipe foi notificada.",
            "sources": [],
            "session_id": session_id or str(uuid.uuid4()),
            "error": "Erro interno do sistema"
        }