"""
Serviço de embeddings usando Sentence Transformers
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


def _normalize_embedding_for_db(embedding: List[float]) -> List[float]:
    arr = np.asarray(embedding, dtype=float)
    if arr.ndim != 1:
        arr = arr.flatten()
    out = arr.tolist()
    if len(out) != EMBEDDING_DIM:
        if len(out) < EMBEDDING_DIM:
            out = out + [0.0] * (EMBEDDING_DIM - len(out))
        else:
            out = out[:EMBEDDING_DIM]
    return out


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
            embedding = await loop.run_in_executor(
                None, lambda: self.model.encode([clean_text], convert_to_numpy=True)[0]
            )
            return _normalize_embedding_for_db(embedding.tolist())
        except Exception as exc:  # pragma: no cover - runtime error handling
            logger.error("Erro ao gerar embedding: %s", exc)
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
            try:
                if hasattr(emb_val, "tolist"):
                    return _normalize_embedding_for_db(list(emb_val.tolist()))
                if isinstance(emb_val, (list, tuple)):
                    return _normalize_embedding_for_db(list(emb_val))
                if isinstance(emb_val, memoryview):
                    return _normalize_embedding_for_db(list(emb_val.tolist()))
                if isinstance(emb_val, str):
                    s = emb_val.strip("{} \n\t")
                    if s == "":
                        return None
                    return _normalize_embedding_for_db([float(x) for x in s.split(",") if x != ""])
                return _normalize_embedding_for_db(list(emb_val))
            except Exception as conv_e:  # pragma: no cover - defensive
                logger.warning("Erro convertendo embedding do cache: %s", conv_e)
                return None
        except Exception as exc:  # pragma: no cover - db error
            logger.warning("Erro ao buscar embedding em cache: %s", exc)
            return None
        finally:
            db.close()

    async def cache_embedding(self, query_text: str, embedding: List[float]) -> None:
        text_hash = self._get_text_hash(query_text)
        db = SessionLocal()
        try:
            exists_stmt = select(QueryEmbeddingCache).where(QueryEmbeddingCache.query_hash == text_hash)
            exists = db.execute(exists_stmt).scalar_one_or_none()
            if exists:
                return
            record = QueryEmbeddingCache(query_text=query_text[:500], query_hash=text_hash, embedding=_normalize_embedding_for_db(embedding))
            db.add(record)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
        except Exception as exc:  # pragma: no cover - db error
            logger.warning("Erro ao salvar embedding em cache: %s", exc)
        finally:
            db.close()

    async def get_query_embedding(self, query: str) -> List[float]:
        if not query or not query.strip():
            return [0.0] * EMBEDDING_DIM
        cached = await self.get_cached_embedding(query)
        if cached:
            return cached
        embedding = await self.generate_embedding(query)
        asyncio.create_task(self.cache_embedding(query, embedding))
        return embedding


embedding_service = EmbeddingService()


async def find_similar_politicians(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    query_embedding = await embedding_service.get_query_embedding(query)
    query_embedding = _normalize_embedding_for_db(query_embedding)
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
        result = db.execute(stmt, {"q_emb": query_embedding}).mappings().all()
        return [dict(row) for row in result]
    except Exception as exc:  # pragma: no cover - runtime
        logger.error("Erro na busca de políticos por embedding: %s", exc)
        return []
    finally:
        db.close()


async def find_similar_documents(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    query_embedding = await embedding_service.get_query_embedding(query)
    query_embedding = _normalize_embedding_for_db(query_embedding)
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
        result = db.execute(stmt, {"q_emb": query_embedding}).mappings().all()
        return [dict(row) for row in result]
    except Exception as exc:  # pragma: no cover - runtime
        logger.error("Erro na busca de documentos por embedding: %s", exc)
        return []
    finally:
        db.close()


async def update_politician_embeddings() -> None:
    db = SessionLocal()
    try:
        stmt = select(Politico).where(Politico.biografia_resumo.is_not(None), Politico.embedding_biografia.is_(None)).limit(10)
        rows = db.execute(stmt).scalars().all()
        for pol in rows:
            if pol.biografia_resumo:
                embedding = await embedding_service.generate_embedding(pol.biografia_resumo)
                pol.embedding_biografia = _normalize_embedding_for_db(embedding)
        db.commit()
    except Exception as exc:  # pragma: no cover - runtime
        logger.error("Erro ao atualizar embeddings de políticos: %s", exc)
    finally:
        db.close()


async def update_document_embeddings() -> None:
    db = SessionLocal()
    try:
        stmt = select(DocumentoPolitico).where(
            (
                DocumentoPolitico.embedding_titulo.is_(None)
                | DocumentoPolitico.embedding_ementa.is_(None)
            ),
            DocumentoPolitico.titulo.is_not(None),
        ).limit(10)
        rows = db.execute(stmt).scalars().all()
        for doc in rows:
            if doc.titulo and getattr(doc, "embedding_titulo", None) is None:
                doc.embedding_titulo = _normalize_embedding_for_db(await embedding_service.generate_embedding(doc.titulo))
            if doc.ementa and getattr(doc, "embedding_ementa", None) is None:
                doc.embedding_ementa = _normalize_embedding_for_db(await embedding_service.generate_embedding(doc.ementa))
            content = doc.conteudo_original or doc.resumo_simplificado
            if content and getattr(doc, "embedding_documento", None) is None:
                doc.embedding_documento = _normalize_embedding_for_db(await embedding_service.generate_embedding(content))
        db.commit()
    except Exception as exc:  # pragma: no cover - runtime
        logger.error("Erro ao atualizar embeddings de documentos: %s", exc)
    finally:
        db.close()
