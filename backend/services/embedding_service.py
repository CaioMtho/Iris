"""
Serviço de embeddings
"""

import hashlib
import logging
import asyncio
from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import bindparam, func, select
from sqlalchemy.exc import IntegrityError

from backend.db.database import SessionLocal
from backend.models.models import ( 
    DocumentoPolitico,
    Politico,
    QueryEmbeddingCache,
)

logger = logging.getLogger(__name__)

MODEL_NAME = "neuralmind/bert-base-portuguese-cased"
EMBEDDING_DIM = 768
SIMILARITY_THRESHOLD = 0.7


def _normalize_embedding_for_db(embedding: Any) -> List[float]:
    """
    Normalização robusta de embeddings para formato compatível com pgvector
    """
    try:
        if isinstance(embedding, list):
            arr = np.array(embedding, dtype=np.float32)
        elif isinstance(embedding, np.ndarray):
            arr = embedding.astype(np.float32)
        elif hasattr(embedding, 'tolist'):
            arr = np.array(embedding.tolist(), dtype=np.float32)
        else:
            arr = np.asarray(embedding, dtype=np.float32)
        
        if arr.ndim == 0:
            logger.warning("Embedding é escalar, criando array de zeros")
            return [0.0] * EMBEDDING_DIM
        elif arr.ndim > 1:
            logger.debug(f"Achatando embedding de shape {arr.shape}")
            arr = arr.flatten()
        
        if arr.size == 0:
            logger.warning("Embedding vazio, criando array de zeros")
            return [0.0] * EMBEDDING_DIM
        
        if len(arr) < EMBEDDING_DIM:
            padded = np.zeros(EMBEDDING_DIM, dtype=np.float32)
            padded[:len(arr)] = arr
            arr = padded
        elif len(arr) > EMBEDDING_DIM:
            arr = arr[:EMBEDDING_DIM]
        
        # Verificar se há valores inválidos
        if not np.isfinite(arr).all():
            logger.warning("Embedding contém valores inválidos (NaN/Inf), substituindo por zeros")
            arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        
        result = [float(x) for x in arr]
        
        if len(result) != EMBEDDING_DIM:
            logger.error(f"Embedding final tem tamanho incorreto: {len(result)}, esperado: {EMBEDDING_DIM}")
            return [0.0] * EMBEDDING_DIM
        
        return result
        
    except Exception as e:
        logger.error(f"Erro na normalização do embedding: {e}, tipo: {type(embedding)}")
        return [0.0] * EMBEDDING_DIM


class EmbeddingService:
    def __init__(self) -> None:
        self.model: Optional[SentenceTransformer] = None
        self._lock = asyncio.Lock()

    async def _ensure_model_loaded(self) -> None:
        if self.model is None:
            async with self._lock:
                if self.model is None:
                    loop = asyncio.get_event_loop()
                    self.model = await loop.run_in_executor(
                        None, lambda: SentenceTransformer(MODEL_NAME, device="cpu")
                    )

    async def generate_embedding(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIM
        
        await self._ensure_model_loaded()
        clean_text = text.strip().replace("\n", " ")[:512]
        
        try:
            loop = asyncio.get_event_loop()
            raw_embedding = await loop.run_in_executor(
                None, lambda: self.model.encode([clean_text], convert_to_numpy=True)
            )
            
            if isinstance(raw_embedding, np.ndarray) and raw_embedding.ndim == 2:
                embedding_vector = raw_embedding[0]
            else:
                embedding_vector = raw_embedding
            
            logger.debug(f"Embedding gerado - shape: {getattr(embedding_vector, 'shape', 'N/A')}, tipo: {type(embedding_vector)}")
            
            return _normalize_embedding_for_db(embedding_vector)
            
        except Exception as exc:
            logger.error(f"Erro ao gerar embedding: {exc}")
            return [0.0] * EMBEDDING_DIM

    def _get_text_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        text_hash = self._get_text_hash(text)
        db = SessionLocal()
        try:
            stmt = select(QueryEmbeddingCache).where(QueryEmbeddingCache.query_hash == text_hash)
            row = db.execute(stmt).scalar_one_or_none()
            if row is None:
                return None
            
            emb_val = row.embedding
            if emb_val is None:
                return None
            
            try:
                normalized = _normalize_embedding_for_db(emb_val)
                logger.debug(f"Embedding do cache normalizado - tamanho: {len(normalized)}")
                return normalized
            except Exception as conv_e:
                logger.warning(f"Erro convertendo embedding do cache: {conv_e}. Removendo entrada inválida.")
                db.delete(row)
                db.commit()
                return None
                
        except Exception as exc:
            logger.warning(f"Erro ao buscar embedding em cache: {exc}")
            return None
        finally:
            db.close()

    async def cache_embedding(self, query_text: str, embedding: List[float]) -> None:
        normalized_embedding = _normalize_embedding_for_db(embedding)
        if len(normalized_embedding) != EMBEDDING_DIM:
            logger.error(f"Tentativa de cachear embedding com tamanho incorreto: {len(normalized_embedding)}")
            return
        
        text_hash = self._get_text_hash(query_text)
        db = SessionLocal()
        try:
            exists_stmt = select(QueryEmbeddingCache).where(QueryEmbeddingCache.query_hash == text_hash)
            exists = db.execute(exists_stmt).scalar_one_or_none()
            if exists:
                return
                
            record = QueryEmbeddingCache(
                query_text=query_text[:500], 
                query_hash=text_hash, 
                embedding=normalized_embedding
            )
            db.add(record)
            try:
                db.commit()
                logger.debug(f"Embedding cacheado com sucesso para query: {query_text[:50]}...")
            except IntegrityError:
                db.rollback()
                logger.debug("Embedding já existe no cache (conflito de integridade)")
        except Exception as exc:
            logger.warning(f"Erro ao salvar embedding em cache: {exc}")
        finally:
            db.close()

    async def get_query_embedding(self, query: str) -> List[float]:
        if not query or not query.strip():
            return [0.0] * EMBEDDING_DIM
        
        cached = await self.get_cached_embedding(query)
        if cached:
            logger.debug("Usando embedding do cache")
            return cached
        
        logger.debug("Gerando novo embedding")
        embedding = await self.generate_embedding(query)
        
        asyncio.create_task(self.cache_embedding(query, embedding))
        
        return embedding


embedding_service = EmbeddingService()


async def find_similar_politicians(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Busca políticos similares usando embedding, com tratamento robusto de erros"""
    try:
        query_embedding = await embedding_service.get_query_embedding(query)
        
        if not isinstance(query_embedding, list):
            logger.error(f"Query embedding não é lista: {type(query_embedding)}")
            return []
        
        if len(query_embedding) != EMBEDDING_DIM:
            logger.error(f"Query embedding tem tamanho incorreto: {len(query_embedding)}")
            return []
        
        if not all(isinstance(x, (int, float)) and np.isfinite(x) for x in query_embedding):
            logger.error("Query embedding contém valores inválidos")
            return []
        
        try:
            from pgvector import Vector
            pgvector_embedding = Vector(query_embedding)
            logger.debug(f"Embedding convertido para pgvector com sucesso (dim: {len(query_embedding)})")
        except Exception as conv_err:
            logger.error(f"Erro ao converter embedding para pgvector: {conv_err}")
            logger.error(f"Embedding problemático: type={type(query_embedding)}, len={len(query_embedding)}")
            return []
        
        logger.debug(f"Buscando políticos similares com embedding válido (tamanho: {len(query_embedding)})")
        
        db = SessionLocal()
        try:
            qparam = bindparam("q_emb")
            sim_expr = (1 - Politico.embedding_biografia.op("<=>")(qparam)).label("similarity")
            stmt = (
                select(
                    Politico.id,
                    Politico.id_camara,
                    Politico.nome,
                    Politico.partido,
                    Politico.uf,
                    Politico.cargo,
                    Politico.biografia_resumo,
                    Politico.ativo,
                    sim_expr,
                )
                .where(
                    Politico.embedding_biografia.is_not(None),
                    Politico.ativo.is_(True),
                    sim_expr > SIMILARITY_THRESHOLD,
                )
                .order_by(sim_expr.desc())
                .limit(limit)
            )
            result = db.execute(stmt, {"q_emb": pgvector_embedding}).mappings().all()
            logger.debug(f"Encontrados {len(result)} políticos similares")
            return [dict(row) for row in result]
            
        finally:
            db.close()
            
    except Exception as exc:
        logger.exception(f"Erro na busca de políticos por embedding: {exc}")
        return []


async def find_similar_documents(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Busca documentos similares usando embedding, com tratamento robusto de erros"""
    try:
        query_embedding = await embedding_service.get_query_embedding(query)
        
        if not isinstance(query_embedding, list):
            logger.error(f"Query embedding não é lista: {type(query_embedding)}")
            return []
        
        if len(query_embedding) != EMBEDDING_DIM:
            logger.error(f"Query embedding tem tamanho incorreto: {len(query_embedding)}")
            return []
        
        if not all(isinstance(x, (int, float)) and np.isfinite(x) for x in query_embedding):
            logger.error("Query embedding contém valores inválidos")
            return []
        
        try:
            from pgvector import Vector
            pgvector_embedding = Vector(query_embedding)
            logger.debug(f"Embedding convertido para pgvector com sucesso (dim: {len(query_embedding)})")
        except Exception as conv_err:
            logger.error(f"Erro ao converter embedding para pgvector: {conv_err}")
            logger.error(f"Embedding problemático: type={type(query_embedding)}, len={len(query_embedding)}")
            logger.error(f"Primeiros 5 valores: {query_embedding[:5] if len(query_embedding) > 5 else query_embedding}")
            return []
        
        logger.debug(f"Buscando documentos similares com embedding válido (tamanho: {len(query_embedding)})")
        
        db = SessionLocal()
        try:
            qparam = bindparam("q_emb")
            sim_title = func.coalesce(1 - DocumentoPolitico.embedding_titulo.op("<=>")(qparam), 0)
            sim_ementa = func.coalesce(1 - DocumentoPolitico.embedding_ementa.op("<=>")(qparam), 0)
            sim_doc = func.coalesce(1 - DocumentoPolitico.embedding_documento.op("<=>")(qparam), 0)
            max_similarity = func.greatest(sim_title, sim_ementa, sim_doc).label("max_similarity")
            
            stmt = (
                select(
                    DocumentoPolitico.id,
                    DocumentoPolitico.id_documento_origem,
                    DocumentoPolitico.titulo,
                    DocumentoPolitico.ementa,
                    DocumentoPolitico.resumo_simplificado,
                    DocumentoPolitico.conteudo_original,
                    DocumentoPolitico.url_fonte,
                    max_similarity,
                )
                .where(
                    (DocumentoPolitico.embedding_titulo.is_not(None)
                     | DocumentoPolitico.embedding_ementa.is_not(None)
                     | DocumentoPolitico.embedding_documento.is_not(None)),
                    max_similarity > (SIMILARITY_THRESHOLD - 0.1),
                )
                .order_by(max_similarity.desc())
                .limit(limit)
            )
            
            result = db.execute(stmt, {"q_emb": pgvector_embedding}).mappings().all()
            logger.debug(f"Encontrados {len(result)} documentos similares")
            return [dict(row) for row in result]
            
        finally:
            db.close()
            
    except Exception as exc:
        logger.exception(f"Erro na busca de documentos por embedding: {exc}")
        return []


async def validate_and_fix_stored_embeddings() -> None:
    """Valida e corrige embeddings corrompidos no banco de dados"""
    db = SessionLocal()
    try:
        logger.info("Validando embeddings de políticos...")
        stmt = select(Politico).where(Politico.embedding_biografia.is_not(None)).limit(100)
        politicos = db.execute(stmt).scalars().all()
        
        for pol in politicos:
            try:
                if pol.embedding_biografia:
                    from pgvector import Vector
                    Vector(pol.embedding_biografia)
            except Exception as e:
                logger.warning(f"Embedding corrompido encontrado para político {pol.nome}: {e}")
                pol.embedding_biografia = None
        
        logger.info("Validando embeddings de documentos...")
        stmt = select(DocumentoPolitico).where(
            (DocumentoPolitico.embedding_titulo.is_not(None) |
             DocumentoPolitico.embedding_ementa.is_not(None) |
             DocumentoPolitico.embedding_documento.is_not(None))
        ).limit(100)
        docs = db.execute(stmt).scalars().all()
        
        for doc in docs:
            try:
                from pgvector import Vector
                if doc.embedding_titulo:
                    Vector(doc.embedding_titulo)
                if doc.embedding_ementa:
                    Vector(doc.embedding_ementa) 
                if doc.embedding_documento:
                    Vector(doc.embedding_documento)
            except Exception as e:
                logger.warning(f"Embedding corrompido encontrado para documento {doc.titulo}: {e}")
                doc.embedding_titulo = None
                doc.embedding_ementa = None
                doc.embedding_documento = None
        
        db.commit()
        logger.info("Validação de embeddings concluída")
        
    except Exception as exc:
        logger.error(f"Erro na validação de embeddings: {exc}")
        db.rollback()
    finally:
        db.close()


async def update_politician_embeddings() -> None:
    """Atualiza embeddings de políticos com tratamento robusto"""
    db = SessionLocal()
    try:
        stmt = select(Politico).where(
            Politico.biografia_resumo.is_not(None), 
        ).limit(10)
        rows = db.execute(stmt).scalars().all()
        
        for pol in rows:
            if pol.biografia_resumo:
                try:
                    embedding = await embedding_service.generate_embedding(pol.biografia_resumo)
                    normalized = _normalize_embedding_for_db(embedding)
                    
                    if len(normalized) == EMBEDDING_DIM:
                        pol.embedding_biografia = normalized
                        logger.debug(f"Embedding atualizado para político: {pol.nome}")
                    else:
                        logger.error(f"Embedding inválido para político {pol.nome}: tamanho {len(normalized)}")
                        
                except Exception as e:
                    logger.error(f"Erro ao processar embedding para político {pol.nome}: {e}")
                    
        db.commit()
        logger.info(f"Processados {len(rows)} políticos para atualização de embeddings")
        
    except Exception as exc:
        logger.error(f"Erro ao atualizar embeddings de políticos: {exc}")
        db.rollback()
    finally:
        db.close()


async def update_document_embeddings() -> None:
    """Atualiza embeddings de documentos com tratamento robusto"""
    db = SessionLocal()
    try:
        stmt = select(DocumentoPolitico).where(
            DocumentoPolitico.titulo.is_not(None),
        ).limit(10)
        rows = db.execute(stmt).scalars().all()
        
        for doc in rows:
            try:
                # Título
                if doc.titulo and getattr(doc, "embedding_titulo", None) is None:
                    embedding = await embedding_service.generate_embedding(doc.titulo)
                    normalized = _normalize_embedding_for_db(embedding)
                    if len(normalized) == EMBEDDING_DIM:
                        doc.embedding_titulo = normalized
                
                # Ementa
                if doc.ementa and getattr(doc, "embedding_ementa", None) is None:
                    embedding = await embedding_service.generate_embedding(doc.ementa)
                    normalized = _normalize_embedding_for_db(embedding)
                    if len(normalized) == EMBEDDING_DIM:
                        doc.embedding_ementa = normalized
                
                # Documento
                content = doc.conteudo_original or doc.resumo_simplificado
                if content and getattr(doc, "embedding_documento", None) is None:
                    embedding = await embedding_service.generate_embedding(content)
                    normalized = _normalize_embedding_for_db(embedding)
                    if len(normalized) == EMBEDDING_DIM:
                        doc.embedding_documento = normalized
                        
                logger.debug(f"Embeddings atualizados para documento: {doc.titulo[:50]}...")
                
            except Exception as e:
                logger.error(f"Erro ao processar embeddings para documento {doc.titulo}: {e}")
                
        db.commit()
        logger.info(f"Processados {len(rows)} documentos para atualização de embeddings")
        
    except Exception as exc:
        logger.error(f"Erro ao atualizar embeddings de documentos: {exc}")
        db.rollback()
    finally:
        db.close()