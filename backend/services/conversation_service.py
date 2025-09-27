"""
Serviço de conversa
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

IRIS_NAME = "Iris"
MAX_HISTORY_MESSAGES = 50
MAX_SNIPPET_CHARS = 800


SYSTEM_BIO = (
    f"Eu sou {IRIS_NAME}, uma assistente de análise política automatizada.\n\n"
    "- Posso explicar e definir termos técnicos, jurídicos e políticos;\n"
    "- Fornecer contexto sobre pessoas envolvidas com política quando houver dados;\n"
    "- Consultar a base de dados do sistema para fatos e votações e citar as fontes encontradas;\n"
    "- Ser transparente sobre limitações: não invento fatos."
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


def _build_search_terms(q: str) -> List[str]:
    txt = _normalize_query(q)
    if not txt:
        return []
    tokens = [t for t in re.split(r"\s+", txt) if t]
    terms: List[str] = []
    if len(tokens) >= 2:
        terms.append(" ".join(tokens))
        terms.append(tokens[-1])
    else:
        terms.append(txt)
    for t in tokens:
        if len(t) > 2 and t not in terms:
            terms.append(t)
    seen = set()
    out: List[str] = []
    for t in terms:
        low = t.lower()
        if low not in seen:
            seen.add(low)
            out.append(t)
    return out


def _fetch_politico_by_terms(q: str, limit: int = 1) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        terms = _build_search_terms(q)
        if not terms:
            return []
        patterns = [f"%{t}%" for t in terms]
        conditions = []
        for p in patterns:
            conditions.append(Politico.nome.ilike(p))
        conditions.append(Politico.partido.ilike(f"%{q}%"))
        conditions.append(Politico.uf.ilike(f"%{q}%"))
        conditions.append(Politico.cargo.ilike(f"%{q}%"))
        rows = db.query(Politico).filter(or_(*conditions)).order_by(Politico.nome.asc()).limit(limit).all()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": str(r.id),
                    "id_camara": r.id_camara,
                    "nome": r.nome,
                    "partido": r.partido,
                    "uf": r.uf,
                    "cargo": r.cargo,
                    "ativo": r.ativo,
                }
            )
        return out
    finally:
        db.close()


def _fetch_votos_for_politico(politico_id: str) -> List[Dict[str, Any]]:
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
        votes: List[Dict[str, Any]] = []
        for r in rows:
            votes.append(
                {
                    "document_id": r["doc_id"],
                    "document_uuid": str(r["documento_uuid"]),
                    "titulo": r["titulo"],
                    "voto": r["voto"],
                }
            )
        return votes
    finally:
        db.close()


def _fetch_documents_matching_query(q: str, limit: int = 4) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        terms = _build_search_terms(q)
        patterns = [f"%{t}%" for t in terms] if terms else [f"%{q}%"]
        conditions = []
        for p in patterns:
            conditions.append(DocumentoPolitico.titulo.ilike(p))
            conditions.append(DocumentoPolitico.ementa.ilike(p))
            conditions.append(DocumentoPolitico.resumo_simplificado.ilike(p))
            conditions.append(DocumentoPolitico.conteudo_original.ilike(p))
        rows = (
            db.query(DocumentoPolitico)
            .filter(or_(*conditions))
            .order_by(DocumentoPolitico.created_at.desc())
            .limit(limit)
            .all()
        )
        out: List[Dict[str, Any]] = []
        for r in rows:
            content = (r.conteudo_original or r.resumo_simplificado or r.ementa or r.titulo or "")
            out.append(
                {
                    "id": str(r.id),
                    "id_documento_origem": r.id_documento_origem,
                    "titulo": r.titulo,
                    "snippet": _snippet(content),
                    "content": content.strip(),
                    "url_fonte": r.url_fonte,
                }
            )
        return out
    finally:
        db.close()


def _build_deterministic_summary_from_db(politico: Dict[str, Any], votes: List[Dict[str, Any]]) -> Dict[str, Any]:
    nome = politico.get("nome")
    partido = politico.get("partido") or "Desconhecido"
    uf = politico.get("uf") or ""
    cargo = politico.get("cargo") or "representante público"
    header = f"{nome} é {cargo} ({partido}-{uf})."
    sim_count = sum(1 for v in votes if (v.get("voto") or "").upper() == "SIM")
    nao_count = sum(1 for v in votes if (v.get("voto") or "").upper() == "NAO")
    abst_count = sum(1 for v in votes if (v.get("voto") or "").upper() == "ABSTENCAO")
    ausente_count = sum(1 for v in votes if (v.get("voto") or "").upper() == "AUSENTE")
    total_known = len(votes)
    if total_known > 0:
        stats = f"Dos {total_known} votos registrados na base, {sim_count} foram SIM e {nao_count} foram NÃO."
        examples = []
        for v in votes[:3]:
            examples.append(f"{v.get('titulo')}: {v.get('voto')}")
        evidence_text = "; ".join(examples)
        summary = f"{header} {stats} Exemplos: {evidence_text}."
    else:
        summary = f"{header} Não há votos registrados na base para este político."
    return {
        "summary": summary,
        "sim_count": sim_count,
        "nao_count": nao_count,
        "abst_count": abst_count,
        "ausente_count": ausente_count,
        "total_known": total_known,
        "examples": votes[:3],
    }


def _is_definition_query(q: str) -> bool:
    if not q:
        return False
    q = q.strip().lower()
    return bool(re.match(r"^(o que é|o que sao|o que são|defina|definição|explique|como funciona|qual é a definição de)\b", q))


def _is_self_intro_query(q: str) -> bool:
    if not q:
        return False
    low = q.strip().lower()
    triggers = ["se apresente", "apresente-se", "apresente se", "apresente", "quem é você", "quem é iris", "olá iris", "oi iris"]
    for t in triggers:
        if t in low:
            return True
    if re.search(r"(?i)\b(se apresente|apresente-se)\b", q):
        return True
    return False


def _clean_model_text(text: str) -> str:
    if not text:
        return text
    text = text.strip()
    patterns = [
        r"(?i)^\s*aqui está o texto parafraseado[:\-]*\s*",
        r"(?i)^\s*aqui está[:\-]*\s*",
        r"(?i)^\s*resposta[:\-]*\s*",
        r"(?i)^\s*responda[:\-]*\s*",
        r"(?i)^\s*here is[:\-]*\s*",
    ]
    for p in patterns:
        text = re.sub(p, "", text)
    return text.strip()


def _documents_relevant_for_query(user_message: str, documents: List[Dict[str, Any]]) -> bool:
    if not documents:
        return False
    tokens = [t.lower() for t in re.split(r"\s+", _normalize_query(user_message)) if len(t) > 3]
    if not tokens:
        return False
    for d in documents:
        hay = (d.get("titulo") or "") + " " + (d.get("snippet") or "")
        hay = hay.lower()
        for tk in tokens:
            if tk in hay:
                return True
    return False


def _doc_has_substantive_text(doc: Dict[str, Any], min_chars: int = 120) -> bool:
    content = (doc.get("content") or "") or (doc.get("snippet") or "")
    cnt = len(re.sub(r"\s+", "", content))
    return cnt >= min_chars


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
        model_text = SYSTEM_BIO
        save_session_message(session_id, "assistant", model_text)
        log_response(json.dumps({"type": "self_intro"}, ensure_ascii=False), model_text, session_id, user_id, [])
        elapsed = time.time() - start
        return {
            "response": model_text,
            "evidence": [],
            "sources": [],
            "session_id": session_id,
            "processing_time": elapsed,
        }

    politicos = _fetch_politico_by_terms(user_message, limit=1)
    documents = _fetch_documents_matching_query(user_message, limit=4)

    if politicos:
        politico = politicos[0]
        votes = _fetch_votos_for_politico(politico["id"])
        deterministic = _build_deterministic_summary_from_db(politico, votes)
        paraphrase_prompt = (
            "Reescreva em português, em 1-2 frases, o texto factual abaixo SEM ADICIONAR INFORMAÇÕES. "
            "Retorne apenas o texto sem cabeçalhos.\n\n"
            f"TEXT_TO_PARAPHRASE:\n{deterministic['summary']}\n\n"
            "RETORNE APENAS O TEXTO PARAFRASEADO."
        )
        try:
            model_out = await generate_from_ollama(
                paraphrase_prompt,
                session_id=session_id,
                user_name=user_id or "anonymous",
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception:
            model_out = None

        if isinstance(model_out, dict):
            model_text = model_out.get("text") or model_out.get("content") or json.dumps(model_out, ensure_ascii=False)
        elif isinstance(model_out, str) and model_out.strip():
            model_text = model_out.strip()
        else:
            model_text = deterministic["summary"]

        model_text = _clean_model_text(model_text)

        evidence: List[Dict[str, Any]] = []
        for ex in deterministic.get("examples", []):
            evidence.append({"text": f"{ex.get('titulo')}: {ex.get('voto')}", "source": ex.get("document_id"), "location": ex.get("document_id")})

        sources: List[Dict[str, Any]] = [
            {"id": f"politico-{politico.get('id_camara')}", "title": politico.get("nome"), "type": "deputado"}
        ]
        for d in documents:
            sources.append({"id": d.get("id_documento_origem"), "title": d.get("titulo"), "type": "documento"})

        save_session_message(session_id, "assistant", model_text)
        log_response(json.dumps({"type": "politico", "data": deterministic}, ensure_ascii=False), model_text, session_id, user_id, [s.get("id") for s in sources])
        elapsed = time.time() - start
        return {
            "response": model_text,
            "evidence": evidence,
            "sources": sources,
            "session_id": session_id,
            "processing_time": elapsed,
        }

    is_def = _is_definition_query(user_message)
    docs_relevant = _documents_relevant_for_query(user_message, documents)
    has_docs = bool(documents)
    has_substantive = any(_doc_has_substantive_text(d) for d in documents) if has_docs else False

    if is_def:
        if has_docs and docs_relevant and has_substantive:
            content_blocks: List[str] = []
            for d in documents[:3]:
                c = (d.get("content") or "").strip()
                if c:
                    content_blocks.append(f"{d.get('titulo')}\n\n{c}")
                else:
                    s = d.get("snippet") or ""
                    if s:
                        content_blocks.append(f"{d.get('titulo')}\n\n{s}")
                    else:
                        content_blocks.append(d.get("titulo") or "")
            summary_text = "\n\n".join([b for b in content_blocks if b.strip()])

            paraphrase_prompt = (
                "Componha uma explicação clara, em português, com base apenas no texto abaixo. "
                "Não adicione informações. Retorne apenas o parágrafo final sem cabeçalhos.\n\n"
                f"TEXT_TO_PARAPHRASE:\n{summary_text}\n\nRETORNE APENAS O TEXTO PARAFRASEADO."
            )
            try:
                model_out = await generate_from_ollama(
                    paraphrase_prompt,
                    session_id=session_id,
                    user_name=user_id or "anonymous",
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except Exception:
                model_out = None

            if isinstance(model_out, dict):
                model_text = model_out.get("text") or model_out.get("content") or json.dumps(model_out, ensure_ascii=False)
            elif isinstance(model_out, str) and model_out.strip():
                model_text = model_out.strip()
            else:
                model_text = summary_text

            model_text = _clean_model_text(model_text)
            sources = [{"id": d.get("id_documento_origem"), "title": d.get("titulo"), "type": "documento"} for d in documents]
            save_session_message(session_id, "assistant", model_text)
            log_response(json.dumps({"type": "definition_from_docs", "docs": documents}, ensure_ascii=False), model_text, session_id, user_id, [s.get("id") for s in sources])
            elapsed = time.time() - start
            return {
                "response": model_text,
                "evidence": [],
                "sources": sources,
                "session_id": session_id,
                "processing_time": elapsed,
            }

        general_prompt = (
            "Explique claramente, em português, o conceito abaixo. Use conhecimento geral do modelo para responder de forma completa.\n\n"
            f"CONCEITO: {user_message}\n\nRETORNE APENAS O TEXTO."
        )
        try:
            model_out = await generate_from_ollama(
                general_prompt,
                session_id=session_id,
                user_name=user_id or "anonymous",
                max_tokens=max_tokens * 2,
                temperature=temperature,
            )
        except Exception:
            model_out = None

        if isinstance(model_out, dict):
            model_text = model_out.get("text") or model_out.get("content") or json.dumps(model_out, ensure_ascii=False)
        elif isinstance(model_out, str) and model_out.strip():
            model_text = model_out.strip()
        else:
            model_text = "informação insuficiente"

        model_text = _clean_model_text(model_text)
        save_session_message(session_id, "assistant", model_text)
        log_response(json.dumps({"type": "definition_no_docs", "query": user_message}, ensure_ascii=False), model_text, session_id, user_id, [])
        elapsed = time.time() - start
        return {
            "response": model_text,
            "evidence": [],
            "sources": [],
            "session_id": session_id,
            "processing_time": elapsed,
        }

    if documents and _documents_relevant_for_query(user_message, documents) and any(_doc_has_substantive_text(d) for d in documents):
        snippets = [f"{d.get('titulo')}: {_snippet(d.get('content') or d.get('snippet') or '')}" for d in documents[:3]]
        summary_text = " ".join(snippets)
        paraphrase_prompt = (
            "Resuma, em português, em linguagem clara e objetiva, com base apenas no texto abaixo. "
            "Não adicione informações. Retorne apenas o parágrafo final sem cabeçalhos.\n\n"
            f"TEXT_TO_PARAPHRASE:\n{summary_text}\n\nRETORNE APENAS O TEXTO."
        )
        try:
            model_out = await generate_from_ollama(
                paraphrase_prompt,
                session_id=session_id,
                user_name=user_id or "anonymous",
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception:
            model_out = None

        if isinstance(model_out, dict):
            model_text = model_out.get("text") or model_out.get("content") or json.dumps(model_out, ensure_ascii=False)
        elif isinstance(model_out, str) and model_out.strip():
            model_text = model_out.strip()
        else:
            model_text = summary_text

        model_text = _clean_model_text(model_text)
        sources = [{"id": d.get("id_documento_origem"), "title": d.get("titulo"), "type": "documento"} for d in documents]
        save_session_message(session_id, "assistant", model_text)
        log_response(json.dumps({"type": "docs_summary", "docs": documents}, ensure_ascii=False), model_text, session_id, user_id, [s.get("id") for s in sources])
        elapsed = time.time() - start
        return {
            "response": model_text,
            "evidence": [],
            "sources": sources,
            "session_id": session_id,
            "processing_time": elapsed,
        }

    general_prompt = (
        "Responda de forma completa e informativa, em português, à pergunta abaixo usando conhecimento geral do modelo.\n\n"
        f"PERGUNTA: {user_message}\n\nRETORNE APENAS O TEXTO."
    )
    try:
        model_out = await generate_from_ollama(
            general_prompt,
            session_id=session_id,
            user_name=user_id or "anonymous",
            max_tokens=max_tokens * 2,
            temperature=temperature,
        )
    except Exception:
        model_out = None

    if isinstance(model_out, dict):
        model_text = model_out.get("text") or model_out.get("content") or json.dumps(model_out, ensure_ascii=False)
    elif isinstance(model_out, str) and model_out.strip():
        model_text = model_out.strip()
    else:
        model_text = "informação insuficiente"

    model_text = _clean_model_text(model_text)
    save_session_message(session_id, "assistant", model_text)
    log_response(json.dumps({"type": "general_no_docs", "query": user_message}, ensure_ascii=False), model_text, session_id, user_id, [])
    elapsed = time.time() - start
    return {
        "response": model_text,
        "evidence": [],
        "sources": [],
        "session_id": session_id,
        "processing_time": elapsed,
    }
