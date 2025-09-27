import uuid
import logging
from typing import Optional, List, Dict
from datetime import datetime
from backend.db.database import SessionLocal
from backend.models.chat_models import SessionMessage, ResponseLog
from backend.models.models import DocumentoPolitico, Politico
from backend.services.ollama_client import generate_from_ollama
from sqlalchemy import text

logger = logging.getLogger(__name__)

IRIS_NAME = "Iris"
MAX_HISTORY_MESSAGES = 6 
MAX_SNIPPET_CHARS = 600
MAX_CONTEXT_TOKENS = 1500

def _snippet(text: str, chars: int = MAX_SNIPPET_CHARS) -> str:
    """Trunca texto preservando palavras completas"""
    if not text:
        return ""
    s = text.replace("\n", " ").strip()
    if len(s) <= chars:
        return s
    return s[:chars].rsplit(" ", 1)[0] + "..."

def get_session_history(session_id: str, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict]:
    """Busca histórico de mensagens da sessão"""
    try:
        db = SessionLocal()
        try:
            rows = db.query(SessionMessage)\
                    .filter(SessionMessage.session_id == session_id)\
                    .order_by(SessionMessage.created_at.desc())\
                    .limit(limit).all()
            
            messages = []
            rows.reverse()
            
            for row in rows[-4:]:
                messages.append({
                    "role": row.role, 
                    "message": row.message[:150],
                    "created_at": row.created_at.isoformat()
                })
            
            return messages
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {str(e)}")
        return []

def save_session_message(session_id: str, role: str, message: str):
    """Salva mensagem na sessão"""
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
    """Registra log da resposta gerada"""
    try:
        db = SessionLocal()
        try:
            truncated_prompt = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
            rl = ResponseLog(
                session_id=session_id, 
                user_id=user_id, 
                prompt=truncated_prompt, 
                response=response, 
                sources=sources
            )
            db.add(rl)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao salvar log: {str(e)}")

def find_politicians_with_votes(q: str, limit: int = 2) -> List[Dict]:
    """Busca políticos com suas votações do banco"""
    try:
        db = SessionLocal()
        try:
            stop_words = ['quem', 'é', 'eh', 'o', 'a', 'que', 'sobre', 'do', 'da', 'de', 'para']
            terms = [term for term in q.lower().split() if term not in stop_words and len(term) >= 3]
            
            if not terms:
                return []
            
            politicians = []
            for term in terms[:2]:
                pattern = f"%{term}%"
                rows = db.query(Politico).filter(
                    Politico.ativo == True,
                    Politico.nome.ilike(pattern)
                ).limit(limit).all()
                politicians.extend(rows)
            
            if not politicians:
                return []
            
            docs = []
            for politician in politicians[:limit]:
                vote_query = text("""
                    SELECT dp.titulo, dp.ementa, vd.voto 
                    FROM votos_documento vd
                    JOIN documentos_politicos dp ON dp.id = vd.documento_id
                    WHERE vd.politico_id = :politico_id
                    AND dp.tipo = 'votacao'
                    ORDER BY dp.created_at DESC
                    LIMIT 8
                """)
                
                votes_result = db.execute(vote_query, {"politico_id": politician.id}).fetchall()
                
                snippet_parts = [
                    f"Deputado federal {politician.nome} ({politician.partido}-{politician.uf})"
                ]
                
                if votes_result:
                    sim_votes = []
                    nao_votes = []
                    
                    for vote_row in votes_result:
                        titulo = vote_row[0]
                        voto = vote_row[2]
                        
                        projeto_nome = titulo.split('(')[0].strip()
                        if len(projeto_nome) > 40:
                            projeto_nome = projeto_nome[:37] + "..."
                        
                        if voto == 'SIM':
                            sim_votes.append(projeto_nome)
                        elif voto == 'NAO':
                            nao_votes.append(projeto_nome)
                    
                    if sim_votes or nao_votes:
                        snippet_parts.append("Votações registradas:")
                        if sim_votes:
                            snippet_parts.append(f"Votou SIM: {'; '.join(sim_votes[:3])}")
                        if nao_votes:
                            snippet_parts.append(f"Votou NÃO: {'; '.join(nao_votes[:3])}")
                else:
                    snippet_parts.append("Nenhuma votação registrada na base atual")
                
                final_snippet = ". ".join(snippet_parts)
                
                docs.append({
                    "id_documento_origem": f"politico-{politician.id_camara}",
                    "titulo": f"{politician.nome} ({politician.partido}-{politician.uf})",
                    "url_fonte": None,
                    "snippet": final_snippet[:MAX_SNIPPET_CHARS],
                    "tipo": "deputado"
                })
            
            return docs
            
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro na busca de políticos: {str(e)}")
        return []

def find_voting_documents(q: str, limit: int = 2) -> List[Dict]:
    """Busca documentos de votação"""
    try:
        db = SessionLocal()
        try:
            stop_words = ['quem', 'é', 'eh', 'o', 'a', 'que', 'sobre', 'do', 'da', 'de', 'para']
            terms = [term for term in q.lower().split() if term not in stop_words and len(term) >= 3]
            
            if not terms:
                return []
            
            base_query = db.query(DocumentoPolitico).filter(DocumentoPolitico.tipo == 'votacao')
            
            for term in terms[:2]:
                pattern = f"%{term}%"
                base_query = base_query.filter(
                    (DocumentoPolitico.titulo.ilike(pattern)) |
                    (DocumentoPolitico.ementa.ilike(pattern)) |
                    (DocumentoPolitico.resumo_simplificado.ilike(pattern))
                )
            
            rows = base_query.order_by(DocumentoPolitico.created_at.desc()).limit(limit).all()
            
            docs = []
            for doc in rows:
                vote_query = text("""
                    SELECT p.nome, p.partido, vd.voto 
                    FROM votos_documento vd
                    JOIN politicos p ON p.id = vd.politico_id
                    WHERE vd.documento_id = :doc_id
                    LIMIT 6
                """)
                
                votes_result = db.execute(vote_query, {"doc_id": doc.id}).fetchall()
                
                snippet_parts = [
                    f"Projeto: {doc.titulo}",
                    f"Descrição: {doc.ementa or doc.resumo_simplificado or 'Não disponível'}"
                ]
                
                if votes_result:
                    sim_voters = []
                    nao_voters = []
                    
                    for vote_row in votes_result:
                        nome = vote_row[0]
                        partido = vote_row[1] 
                        voto = vote_row[2]
                        
                        voter_info = f"{nome} ({partido})"
                        
                        if voto == 'SIM':
                            sim_voters.append(voter_info)
                        elif voto == 'NAO':
                            nao_voters.append(voter_info)
                    
                    if sim_voters:
                        snippet_parts.append(f"Votaram SIM: {'; '.join(sim_voters[:3])}")
                    if nao_voters:
                        snippet_parts.append(f"Votaram NÃO: {'; '.join(nao_voters[:3])}")
                
                final_snippet = ". ".join(snippet_parts)
                
                docs.append({
                    "id_documento_origem": doc.id_documento_origem or str(doc.id),
                    "titulo": doc.titulo[:80],
                    "url_fonte": doc.url_fonte,
                    "snippet": final_snippet[:MAX_SNIPPET_CHARS],
                    "tipo": "votacao"
                })
            
            return docs
            
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro na busca de documentos: {str(e)}")
        return []

def is_specific_query(user_message: str) -> bool:
    """Verifica se é pergunta específica sobre dados que temos"""
    specific_indicators = [
        # Nomes específicos
        'nikolas', 'boulos', 'salles', 'tabata', 'russomanno', 'kataguiri', 
        'mandel', 'erika', 'palumbo', 'hercílio',
        # Termos que indicam busca por dados específicos
        'votou', 'voto', 'votação', 'deputado específico', 'perfil do deputado'
    ]
    
    query_lower = user_message.lower()
    return any(indicator in query_lower for indicator in specific_indicators)

SYSTEM_PROMPT_HYBRID = f"""Você é {IRIS_NAME}, assistente de política brasileira da Câmara dos Deputados.

FUNCIONAMENTO:
1. Se há FONTES ESPECÍFICAS: use apenas essas informações, seja factual e objetiva
2. Se NÃO há fontes específicas: responda com conhecimento geral sobre política brasileira

REGRAS PARA FONTES ESPECÍFICAS:
- Use apenas os dados fornecidos das fontes
- Para deputados: mencione partido, UF e votações registradas objetivamente
- Seja imparcial, não especule sobre motivações ou características pessoais
- Cite fontes como [1], [2]

REGRAS PARA PERGUNTAS GERAIS:
- Use conhecimento geral sobre sistema político brasileiro
- Explique conceitos, cargos, processos legislativos
- Seja educativa mas concisa
- Não mencione fontes se não foram fornecidas"""

def build_hybrid_prompt(chat_history: List[Dict], user_message: str, retrieved_docs: List[Dict]) -> str:
    """Constrói prompt híbrido baseado na disponibilidade de fontes"""
    
    history_context = ""
    if chat_history and len(chat_history) > 0:
        last_msg = chat_history[-1]
        if last_msg and last_msg.get("role") == "user":
            history_context = f"Conversa anterior: {last_msg.get('message', '')[:80]}\n\n"
    
    if retrieved_docs:
        # Modo com fontes específicas
        sources_section = "FONTES DISPONÍVEIS:\n"
        for i, doc in enumerate(retrieved_docs, start=1):
            title = doc.get("titulo", "")
            snippet = doc.get("snippet", "")
            doc_type = doc.get("tipo", "documento")
            
            sources_section += f"[{i}] {doc_type.upper()}: {title}\n{snippet}\n\n"
        
        prompt_parts = [
            SYSTEM_PROMPT_HYBRID,
            "",
            history_context,
            sources_section,
            f"PERGUNTA: {user_message}",
            "",
            "RESPOSTA (baseada nas fontes acima):"
        ]
    else:
        # Modo conhecimento geral
        prompt_parts = [
            SYSTEM_PROMPT_HYBRID,
            "",
            history_context,
            f"PERGUNTA GERAL: {user_message}",
            "",
            "RESPOSTA (conhecimento geral sobre política brasileira):"
        ]
    
    return "\n".join(prompt_parts)

async def handle_chat(user_message: str, session_id: Optional[str] = None, 
                      user_id: Optional[str] = None, max_tokens: int = 400, 
                      temperature: float = 0.15) -> Dict:
    """Handler híbrido: RAG específico + conhecimento geral"""
    start_time = datetime.now()
    
    try:
        if not user_message or len(user_message.strip()) < 2:
            return {
                "response": "Por favor, faça uma pergunta sobre política brasileira.",
                "sources": [],
                "session_id": session_id,
                "error": "Entrada inválida"
            }
        
        if len(user_message) > 200:
            user_message = user_message[:200] + "..."
        
        session_id = session_id or str(uuid.uuid4())
        history = get_session_history(session_id)
        
        # Tentar buscar dados específicos apenas se parecer consulta específica
        retrieved_docs = []
        if is_specific_query(user_message):
            docs_politicians = find_politicians_with_votes(user_message, limit=2)
            docs_votings = find_voting_documents(user_message, limit=1)
            retrieved_docs = docs_politicians + docs_votings
            
            logger.info(f"Consulta específica - encontrados {len(retrieved_docs)} documentos")
        else:
            logger.info("Pergunta geral - usando conhecimento base")
        
        # Construir prompt híbrido
        prompt = build_hybrid_prompt(history, user_message, retrieved_docs)
        
        save_session_message(session_id, "user", user_message)
        
        # Ajustar parâmetros baseado no tipo de resposta
        if retrieved_docs:
            # Resposta baseada em dados: mais restritiva
            response_text = await generate_from_ollama(
                prompt, 
                session_id=session_id, 
                user_name=user_id or "anonymous",
                max_tokens=min(max_tokens, 400),
                temperature=0.1  # Mais determinística
            )
        else:
            # Resposta geral: mais flexível
            response_text = await generate_from_ollama(
                prompt, 
                session_id=session_id, 
                user_name=user_id or "anonymous",
                max_tokens=min(max_tokens, 500),
                temperature=0.3  # Mais criativa
            )
        
        save_session_message(session_id, "assistant", response_text)
        
        sources_used = [d.get("id_documento_origem") for d in retrieved_docs if d.get("id_documento_origem")]
        log_response(prompt, response_text, session_id, user_id, sources_used)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Chat processado em {processing_time:.1f}s - Tipo: {'específico' if retrieved_docs else 'geral'}")
        
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
            "response": "Erro interno do sistema. Nossa equipe foi notificada.",
            "sources": [],
            "session_id": session_id or str(uuid.uuid4()),
            "error": "Erro interno"
        }