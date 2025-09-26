import json
from typing import Optional, List, Dict
from backend.db.database import SessionLocal
from backend.models.chat_models import SessionMessage, ResponseLog
from backend.models.models import DocumentoPolitico
from backend.services.ollama_client import generate_from_ollama

IRIS_NAME = "Iris"
MAX_HISTORY_CHARS = 3000
MAX_SNIPPET_CHARS = 800

def _snippet(text: str, chars: int = MAX_SNIPPET_CHARS) -> str:
    if not text:
        return ""
    s = text.replace("\n", " ").strip()
    return (s[:chars] + "...") if len(s) > chars else s

def get_session_history(session_id: str, limit: int = 50) -> List[Dict]:
    db = SessionLocal()
    try:
        rows = db.query(SessionMessage).filter(SessionMessage.session_id == session_id).order_by(SessionMessage.created_at.asc()).limit(limit).all()
        return [{"role": r.role, "message": r.message, "created_at": r.created_at.isoformat()} for r in rows]
    finally:
        db.close()

def save_session_message(session_id: str, role: str, message: str):
    db = SessionLocal()
    try:
        sm = SessionMessage(session_id=session_id, role=role, message=message)
        db.add(sm)
        db.commit()
    finally:
        db.close()

def log_response(prompt: str, response: str, session_id: Optional[str], user_id: Optional[str], sources: List[str]):
    db = SessionLocal()
    try:
        rl = ResponseLog(session_id=session_id, user_id=user_id, prompt=prompt, response=response, sources=sources)
        db.add(rl)
        db.commit()
    finally:
        db.close()

# RAG leve: busca por DocumentoPolitico via SQLAlchemy
def find_documents_for_query(q: str, limit: int = 4) -> List[Dict]:
    db = SessionLocal()
    try:
        pattern = f"%{q}%"
        # procura por título, ementa, resumo_simplificado ou conteudo_original
        rows = db.query(DocumentoPolitico).filter(
            (DocumentoPolitico.titulo.ilike(pattern)) |
            (DocumentoPolitico.ementa.ilike(pattern)) |
            (DocumentoPolitico.resumo_simplificado.ilike(pattern)) |
            (DocumentoPolitico.conteudo_original.ilike(pattern))
        ).order_by(DocumentoPolitico.created_at.desc()).limit(limit).all()
        docs = []
        for r in rows:
            s = r.resumo_simplificado or r.ementa or r.titulo or ""
            docs.append({
                "id_documento_origem": r.id_documento_origem or str(r.id),
                "titulo": r.titulo,
                "url_fonte": r.url_fonte,
                "snippet": _snippet(s)
            })
        return docs
    finally:
        db.close()

# prompt system
SYSTEM_PROMPT = f"""
Você é {IRIS_NAME}, uma assistente de análise política automatizada, especializada em política nacional brasileira.
Regras: não invente fatos; use apenas as fontes fornecidas quando existirem; se não houver informação suficiente, responda 'informação insuficiente'.
"""

def build_prompt(chat_history: List[Dict], user_message: str, retrieved_docs: List[Dict], instruction: Optional[str] = None) -> str:
    history_text = ""
    for m in chat_history:
        role = m.get("role")
        msg = m.get("message")
        if role and msg:
            history_text += f"{role.upper()}: {msg}\n"
    if len(history_text) > MAX_HISTORY_CHARS:
        history_text = history_text[-MAX_HISTORY_CHARS:]
    sources_text = ""
    for i, d in enumerate(retrieved_docs, start=1):
        title = d.get("titulo") or ""
        url = d.get("url_fonte") or ""
        snippet = d.get("snippet") or ""
        sources_text += f"[{i}] {title}\nURL: {url}\nTRECHO: {snippet}\n\n"
    p = SYSTEM_PROMPT + "\n\n"
    if instruction:
        p += f"INSTRUÇÃO: {instruction}\n\n"
    if history_text:
        p += "HISTÓRICO:\n" + history_text + "\n\n"
    if sources_text:
        p += "SOURCES:\n" + sources_text + "\n\n"
    p += f"USUÁRIO: {user_message}\n\nASSISTENTE ({IRIS_NAME}):\n"
    return p

async def handle_chat(user_message: str, session_id: Optional[str] = None, user_id: Optional[str] = None,
                      max_tokens: int = 512, temperature: float = 0.0):
    history = get_session_history(session_id) if session_id else []
    docs = find_documents_for_query(user_message, limit=4)
    prompt = build_prompt(history, user_message, docs)
    if session_id:
        save_session_message(session_id, "user", user_message)
    response_text = await generate_from_ollama(prompt, max_tokens=max_tokens, temperature=temperature)
    if session_id:
        save_session_message(session_id, "assistant", response_text)
    sources_used = [d.get("id_documento_origem") for d in docs]
    log_response(prompt, response_text, session_id, user_id, sources_used)
    return {"assistant": response_text, "sources": sources_used, "session_id": session_id}
