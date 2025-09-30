"""
Serviço de conversa com RAG baseado em embeddings
"""

import uuid
import json
import time
import re
from typing import Optional, List, Dict, Any

from sqlalchemy import or_, text
from backend.db.database import SessionLocal
from backend.models.chat_models import SessionMessage, ResponseLog
from backend.models.models import DocumentoPolitico, Politico
from backend.services.ollama_client import generate_from_ollama
from backend.services.embedding_service import find_similar_politicians, find_similar_documents

IRIS_NAME = "Iris"
MAX_HISTORY_MESSAGES = 50
MAX_SNIPPET_CHARS = 600

SYSTEM_BIO = (
    f"Eu sou {IRIS_NAME}, uma assistente de análise política automatizada.\n\n"
    "- Analiso dados sobre políticos e documentos legislativos do Brasil;\n"
    "- Forneço informações factuais sobre votações, propostas e posicionamentos;\n"
    "- Mantenho neutralidade e imparcialidade nas análises;\n"
    "- Estou em desenvolvimento contínuo para melhor servir o interesse público."
)


def _snippet(text: Optional[str], chars: int = MAX_SNIPPET_CHARS) -> str:
    if not text:
        return ""
    s = str(text).replace("\n", " ").strip()
    return (s[:chars] + "...") if len(s) > chars else s


def get_session_history(session_id: str, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = (
            db.query(SessionMessage)
            .filter(SessionMessage.session_id == session_id)
            .order_by(SessionMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        return [{"role": r.role, "message": r.message, "created_at": r.created_at.isoformat()} for r in rows]
    finally:
        db.close()


def save_session_message(session_id: str, role: str, message: str) -> None:
    db = SessionLocal()
    try:
        sm = SessionMessage(session_id=session_id, role=role, message=message)
        db.add(sm)
        db.commit()
    finally:
        db.close()


def log_response(prompt: str, response: str, session_id: Optional[str], user_id: Optional[str], sources: List[str]) -> None:
    db = SessionLocal()
    try:
        rl = ResponseLog(session_id=session_id, user_id=user_id, prompt=prompt, response=response, sources=sources)
        db.add(rl)
        db.commit()
    finally:
        db.close()


def _normalize_query(q: str) -> str:
    if not q:
        return ""
    q = q.strip()
    m = re.search(r"(?i)^(quem é|quem foi|quem|sobre|fale sobre|diga[ -]?me quem é)\s+(.+)$", q)
    candidate = m.group(2) if m else q
    candidate = re.sub(r"[?¡!,.]+", "", candidate).strip()
    return candidate


def _fetch_politico_votes(politico_id: str) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        sql = text(
            """
            SELECT dp.id_documento_origem AS doc_id,
                   dp.titulo AS titulo,
                   vd.voto AS voto,
                   dp.id AS documento_uuid
            FROM votos_documento vd
            JOIN documentos_politicos dp ON vd.documento_id = dp.id
            WHERE vd.politico_id = :pid
            ORDER BY dp.created_at NULLS LAST, dp.id_documento_origem
            """
        )
        rows = db.execute(sql, {"pid": politico_id}).mappings().all()
        return [
            {
                "document_id": r["doc_id"],
                "document_uuid": str(r["documento_uuid"]),
                "titulo": r["titulo"],
                "voto": r["voto"],
            }
            for r in rows
        ]
    finally:
        db.close()


def _fetch_politico_by_search(q: str, limit: int = 3) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        terms = [term for term in re.split(r"\s+", _normalize_query(q)) if len(term) > 3]
        stop_words = {'que', 'como', 'para', 'com', 'por', 'uma', 'mas', 'não', 'sim', 'uma', 'este', 'esta', 'isso'}
        terms = [t for t in terms if t.lower() not in stop_words]
        patterns = [f"%{term}%" for term in terms] if terms else []
        if not patterns:
            return []
        
        conditions = []
        for p in patterns:
            conditions.extend([
                Politico.nome.ilike(p),
                Politico.partido.ilike(p),
                Politico.uf.ilike(p)
            ])
        
        rows = (
            db.query(Politico)
            .filter(or_(*conditions))
            .filter(Politico.ativo == True)
            .order_by(Politico.nome.asc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                "id": str(r.id),
                "id_camara": r.id_camara,
                "nome": r.nome,
                "partido": r.partido,
                "uf": r.uf,
                "cargo": r.cargo,
                "ativo": r.ativo,
                "biografia_resumo": r.biografia_resumo,
                "similarity": 1.0
            }
            for r in rows
        ]
    finally:
        db.close()


def _fetch_documents_by_search(q: str, limit: int = 4) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        terms = [term for term in re.split(r"\s+", _normalize_query(q)) if len(term) > 3]
        stop_words = {'que', 'como', 'para', 'com', 'por', 'uma', 'mas', 'não', 'sim', 'uma', 'este', 'esta', 'isso'}
        terms = [t for t in terms if t.lower() not in stop_words]
        patterns = [f"%{term}%" for term in terms] if terms else [f"%{q}%"]
        
        conditions = []
        for p in patterns:
            conditions.extend([
                DocumentoPolitico.titulo.ilike(p),
                DocumentoPolitico.ementa.ilike(p),
                DocumentoPolitico.resumo_simplificado.ilike(p),
                DocumentoPolitico.conteudo_original.ilike(p)
            ])
        
        rows = (
            db.query(DocumentoPolitico)
            .filter(or_(*conditions))
            .order_by(DocumentoPolitico.created_at.desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                "id": str(r.id),
                "id_documento_origem": r.id_documento_origem,
                "titulo": r.titulo,
                "ementa": r.ementa,
                "resumo_simplificado": r.resumo_simplificado,
                "conteudo_original": r.conteudo_original,
                "url_fonte": r.url_fonte,
                "max_similarity": 1.0
            }
            for r in rows
        ]
    finally:
        db.close()


def _build_politician_summary(politico: Dict[str, Any], votes: List[Dict[str, Any]]) -> Dict[str, Any]:
    nome = politico.get("nome")
    partido = politico.get("partido", "Partido não informado")
    uf = politico.get("uf", "")
    cargo = politico.get("cargo", "representante público")
    biografia = politico.get("biografia_resumo", "")
    
    sim_count = sum(1 for v in votes if (v.get("voto") or "").upper() == "SIM")
    nao_count = sum(1 for v in votes if (v.get("voto") or "").upper() == "NAO")
    total_votes = len(votes)
    
    context_parts = [f"{nome} é {cargo}"]
    
    if partido and uf:
        context_parts.append(f"pelo partido {partido} ({uf})")
    elif partido:
        context_parts.append(f"do partido {partido}")
    
    if biografia:
        context_parts.append(f". {biografia}")
    
    if total_votes > 0:
        context_parts.append(f" Possui {total_votes} votações registradas")
        if sim_count > 0 or nao_count > 0:
            context_parts.append(f", sendo {sim_count} favoráveis e {nao_count} contrárias")
    
    base_text = "".join(context_parts) + "."
    
    return {
        "context": base_text,
        "sim_count": sim_count,
        "nao_count": nao_count,
        "total_votes": total_votes,
        "examples": votes[:3],
        "biografia": biografia
    }


def _is_definition_query(q: str) -> bool:
    if not q:
        return False
    q = q.strip().lower()
    
    starts_with = bool(re.match(r"^(o que é|o que são|defina|definição|explique|me explique|explique o que|como funciona|qual é a definição|o que significa|qual o conceito)", q))
    
    no_politician_reference = not bool(re.search(r"(deputad[oa]|senador[a]|polític[oa]|vereador[a]|\b[A-Z][a-z]+ [A-Z][a-z]+\b)", q))
    
    return starts_with and no_politician_reference


def _is_self_intro_query(q: str) -> bool:
    if not q:
        return False
    low = q.strip().lower()
    triggers = ["se apresente", "apresente-se", "quem é você", "quem é iris", "olá iris", "oi iris"]
    return any(trigger in low for trigger in triggers)


def _clean_model_response(text: str) -> str:
    if not text:
        return text
    
    text = text.strip()
    
    patterns = [
        r"(?i)^\s*aqui está.*?[:\-]\s*",
        r"(?i)^\s*resposta[:\-]\s*",
        r"(?i)^\s*baseado.*?[:\-]\s*",
        r"(?i)^\s*de acordo.*?[:\-]\s*"
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, "", text)
    
    return text.strip()


def _should_use_embedding_search(query: str) -> bool:
    specific_indicators = [
        "posição", "opinião", "votou", "defende", "apoiou", "contrário", 
        "favor", "política", "ideologia", "tema", "assunto"
    ]
    
    return any(indicator in query.lower() for indicator in specific_indicators)


def _documents_are_relevant(documents: List[Dict[str, Any]], query: str) -> bool:
    if not documents:
        return False
    
    query_terms = set(re.findall(r'\w+', query.lower()))
    query_terms.discard('o')
    query_terms.discard('que')
    query_terms.discard('é')
    query_terms.discard('são')
    query_terms.discard('defina')
    query_terms.discard('definição')
    query_terms.discard('explique')
    
    for doc in documents[:3]:
        content = (doc.get('conteudo_original') or doc.get('resumo_simplificado') or doc.get('ementa') or '').lower()
        titulo = (doc.get('titulo') or '').lower()
        
        for term in query_terms:
            if len(term) > 3 and (term in content or term in titulo):
                return True
    
    return False


async def handle_chat(
    user_message: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.0,
) -> Dict[str, Any]:
    session_id = session_id or str(uuid.uuid4())
    start = time.time()

    save_session_message(session_id, "user", user_message)

    if _is_self_intro_query(user_message):
        save_session_message(session_id, "assistant", SYSTEM_BIO)
        log_response(json.dumps({"type": "self_intro"}, ensure_ascii=False), SYSTEM_BIO, session_id, user_id, [])
        elapsed = time.time() - start
        return {
            "response": SYSTEM_BIO,
            "evidence": [],
            "sources": [],
            "session_id": session_id,
            "processing_time": elapsed,
        }

    is_definition = _is_definition_query(user_message)
    
    use_embeddings = _should_use_embedding_search(user_message)
    
    politicos = []
    if not is_definition:
        if use_embeddings:
            try:
                politicos = await find_similar_politicians(user_message, limit=2)
            except Exception:
                politicos = _fetch_politico_by_search(user_message, limit=2)
        else:
            politicos = _fetch_politico_by_search(user_message, limit=2)
            if not politicos:
                try:
                    politicos = await find_similar_politicians(user_message, limit=2)
                except Exception:
                    politicos = []

    if use_embeddings:
        try:
            documents = await find_similar_documents(user_message, limit=5)
        except Exception:
            documents = _fetch_documents_by_search(user_message, limit=5)
    else:
        documents = _fetch_documents_by_search(user_message, limit=4)
        if not documents:
            try:
                documents = await find_similar_documents(user_message, limit=4)
            except Exception:
                documents = []

    if politicos and len(politicos) > 0:
        politico = politicos[0]
        votes = _fetch_politico_votes(politico["id"])
        summary_data = _build_politician_summary(politico, votes)
        
         
        votos_text = "\n".join(f"- {v.get('titulo')}: {v.get('voto')}" for v in votes)

        context_prompt = f"""
Responda de forma natural e informativa sobre este político brasileiro, baseado apenas nas informações fornecidas:

INFORMAÇÕES:
{summary_data["context"]}

VOTAÇÕES REGISTRADAS:
{votos_text}

PERGUNTA DO USUÁRIO: {user_message}

Responda de forma objetiva e imparcial, mencionando os dados de votação quando relevantes. Se houver muitos votos, mencione os mais recentes ou os mais relevantes. Não adicione informações não fornecidas. Você tem acesso a todos os votos do político, então não diga que não consegue citar todos.
"""

        try:
            model_response = await generate_from_ollama(
                context_prompt,
                session_id=session_id,
                user_name=user_id or "anonymous",
                max_tokens=max_tokens,
                temperature=temperature,
            )
            model_text = _clean_model_response(str(model_response)) if model_response else summary_data['context']
        except Exception:
            model_text = summary_data['context']

        evidence = []
        for vote in summary_data['examples']:
            evidence.append({
                "text": f"{vote.get('titulo')}: {vote.get('voto')}",
                "source": vote.get("document_id"),
                "location": vote.get("document_id")
            })

        sources = [
            {"id": f"politico-{politico.get('id_camara')}", "title": politico.get('nome'), "type": "deputado"}
        ]

        save_session_message(session_id, "assistant", model_text)
        log_response(
            json.dumps({"type": "politico", "data": summary_data}, ensure_ascii=False), 
            model_text, session_id, user_id, [s.get("id") for s in sources]
        )
        elapsed = time.time() - start
        return {
            "response": model_text,
            "evidence": evidence,
            "sources": sources,
            "session_id": session_id,
            "processing_time": elapsed,
        }

    if is_definition and documents and _documents_are_relevant(documents, user_message):
        relevant_content = []
        for doc in documents[:3]:
            content = doc.get('conteudo_original') or doc.get('resumo_simplificado') or doc.get('ementa') or ""
            if content.strip():
                relevant_content.append(f"**{doc.get('titulo')}**\n{_snippet(content, 400)}")
        
        content_text = "\n\n".join(relevant_content)
        
        definition_prompt = f"""
Com base nos documentos abaixo, explique de forma clara e objetiva o conceito solicitado:

DOCUMENTOS:
{content_text}

PERGUNTA: {user_message}

Forneça uma explicação educativa baseada apenas nas informações dos documentos. Mantenha linguagem acessível.
"""

        try:
            model_response = await generate_from_ollama(
                definition_prompt,
                session_id=session_id,
                user_name=user_id or "anonymous",
                max_tokens=max_tokens,
                temperature=temperature,
            )
            model_text = _clean_model_response(str(model_response)) if model_response else content_text[:500]
        except Exception:
            model_text = content_text[:500]

        sources = [
            {"id": d.get("id_documento_origem"), "title": d.get("titulo"), "type": "documento"} 
            for d in documents[:3]
        ]
        
        save_session_message(session_id, "assistant", model_text)
        log_response(
            json.dumps({"type": "definition_from_docs", "docs": documents[:3]}, ensure_ascii=False), 
            model_text, session_id, user_id, [s.get("id") for s in sources]
        )
        elapsed = time.time() - start
        return {
            "response": model_text,
            "evidence": [],
            "sources": sources,
            "session_id": session_id,
            "processing_time": elapsed,
        }

    if documents and len(documents) > 0 and not is_definition:
        relevant_docs = [d for d in documents if d.get('max_similarity', 0) > 0.6][:4]
        
        if relevant_docs:
            doc_summaries = []
            for doc in relevant_docs:
                content = doc.get('conteudo_original') or doc.get('resumo_simplificado') or doc.get('ementa') or ""
                if content.strip():
                    doc_summaries.append(f"**{doc.get('titulo')}**: {_snippet(content, 300)}")
            
            combined_content = "\n\n".join(doc_summaries)
            
            document_prompt = f"""
Com base nos documentos legislativos abaixo, responda à pergunta de forma informativa e objetiva:

DOCUMENTOS:
{combined_content}

PERGUNTA: {user_message}

Responda baseando-se apenas nas informações dos documentos. Seja preciso e imparcial.
"""

            try:
                model_response = await generate_from_ollama(
                    document_prompt,
                    session_id=session_id,
                    user_name=user_id or "anonymous",
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                model_text = _clean_model_response(str(model_response)) if model_response else combined_content[:500]
            except Exception:
                model_text = combined_content[:500]

            sources = [
                {"id": d.get("id_documento_origem"), "title": d.get("titulo"), "type": "documento"} 
                for d in relevant_docs
            ]
            
            save_session_message(session_id, "assistant", model_text)
            log_response(
                json.dumps({"type": "docs_summary", "docs": relevant_docs}, ensure_ascii=False), 
                model_text, session_id, user_id, [s.get("id") for s in sources]
            )
            elapsed = time.time() - start
            return {
                "response": model_text,
                "evidence": [],
                "sources": sources,
                "session_id": session_id,
                "processing_time": elapsed,
            }

    general_prompt = f"""
Responda de forma informativa e educativa à pergunta abaixo sobre política brasileira:

PERGUNTA: {user_message}

Forneça uma resposta clara e objetiva baseada em conhecimento geral, mantendo neutralidade política. Evite adicionar opiniões sobre questões gerais de deputados da base, a menos que seja explicitamente solicitado na pergunta do usuário.
"""

    try:
        model_response = await generate_from_ollama(
            general_prompt,
            session_id=session_id,
            user_name=user_id or "anonymous",
            max_tokens=max_tokens * 2,
            temperature=temperature,
        )
        model_text = _clean_model_response(str(model_response)) if model_response else "Não consegui processar sua consulta adequadamente."
    except Exception:
        model_text = "Sistema temporariamente indisponível. Tente reformular sua pergunta."

    save_session_message(session_id, "assistant", model_text)
    log_response(
        json.dumps({"type": "general_knowledge", "query": user_message}, ensure_ascii=False), 
        model_text, session_id, user_id, []
    )
    elapsed = time.time() - start
    return {
        "response": model_text,
        "evidence": [],
        "sources": [],
        "session_id": session_id,
        "processing_time": elapsed,
    }