"""
Serviço de embeddings
"""

import hashlib
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import bindparam, func, select
from sqlalchemy.exc import IntegrityError
from pgvector.sqlalchemy import Vector as VectorType

from backend.db.database import SessionLocal
from backend.models.models import (
    DocumentoPolitico,
    Politico,
    QueryEmbeddingCache,
)

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "bert-base-portuguese-cased"
MODEL_NAME = "neuralmind/bert-base-portuguese-cased"
EMBEDDING_DIM = 768
SIMILARITY_THRESHOLD = 0.7
MAX_TEXT_LENGTH = 512
CACHE_TTL_DAYS = 30


def _validate_embedding(embedding: np.ndarray) -> bool:
    """Valida embedding quanto a dimensões e valores numéricos"""
    return (
        embedding.size == EMBEDDING_DIM
        and np.isfinite(embedding).all()
    )


def _normalize_embedding(embedding: Any) -> List[float]:
    """Normaliza embedding para formato do banco (lista de floats)"""
    try:
        if isinstance(embedding, list):
            arr = np.array(embedding, dtype=np.float32)
        elif isinstance(embedding, np.ndarray):
            arr = embedding.astype(np.float32)
        elif hasattr(embedding, 'tolist'):
            arr = np.array(embedding.tolist(), dtype=np.float32)
        else:
            arr = np.asarray(embedding, dtype=np.float32)

        if arr.ndim == 0 or arr.size == 0:
            logger.warning("Embedding vazio, retornando zeros")
            return [0.0] * EMBEDDING_DIM

        if arr.ndim > 1:
            arr = arr.flatten()

        if len(arr) != EMBEDDING_DIM:
            logger.warning(f"Embedding com dimensão incorreta: {len(arr)}")
            if len(arr) < EMBEDDING_DIM:
                padded = np.zeros(EMBEDDING_DIM, dtype=np.float32)
                padded[:len(arr)] = arr
                arr = padded
            else:
                arr = arr[:EMBEDDING_DIM]

        if not np.isfinite(arr).all():
            logger.warning("Embedding com valores inválidos, normalizando")
            arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

        return arr.tolist()

    except Exception as e:
        logger.error(f"Erro na normalização: {e}")
        return [0.0] * EMBEDDING_DIM


class EmbeddingService:
    """Serviço singleton para geração e cache de embeddings"""

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.model: Optional[SentenceTransformer] = None
        self._model_lock = asyncio.Lock()
        self._initialized = True

    async def _load_model(self) -> None:
        """Carrega modelo localmente ou faz download se necessário"""
        if self.model is not None:
            return

        async with self._model_lock:
            if self.model is not None:
                return

            loop = asyncio.get_event_loop()

            if MODEL_PATH.exists():
                logger.info(f"Carregando modelo local de {MODEL_PATH}")
                self.model = await loop.run_in_executor(
                    None,
                    lambda: SentenceTransformer(str(MODEL_PATH), device="cpu")
                )
            else:
                logger.info(f"Baixando modelo {MODEL_NAME}")
                MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
                self.model = await loop.run_in_executor(
                    None,
                    lambda: SentenceTransformer(MODEL_NAME, device="cpu")
                )
                await loop.run_in_executor(
                    None,
                    lambda: self.model.save(str(MODEL_PATH))
                )
                logger.info(f"Modelo salvo em {MODEL_PATH}")

    async def generate_embedding(self, text: str) -> List[float]:
        """Gera embedding para texto"""
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIM

        await self._load_model()

        clean_text = text.strip().replace("\n", " ")[:MAX_TEXT_LENGTH]

        try:
            loop = asyncio.get_event_loop()
            raw_embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode([clean_text], convert_to_numpy=True)
            )

            embedding_vector = raw_embedding[0] if raw_embedding.ndim == 2 else raw_embedding

            if not _validate_embedding(embedding_vector):
                logger.error("Embedding gerado inválido")
                return [0.0] * EMBEDDING_DIM

            return _normalize_embedding(embedding_vector)

        except Exception as exc:
            logger.error(f"Erro ao gerar embedding: {exc}")
            return [0.0] * EMBEDDING_DIM

    @staticmethod
    def _compute_hash(text: str) -> str:
        """Calcula hash SHA256 do texto"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Busca embedding no cache"""
        text_hash = self._compute_hash(text)
        db = SessionLocal()
        try:
            stmt = select(QueryEmbeddingCache).where(
                QueryEmbeddingCache.query_hash == text_hash
            )
            row = db.execute(stmt).scalar_one_or_none()

            if row is None or row.embedding is None:
                return None

            normalized = _normalize_embedding(row.embedding)
            if len(normalized) != EMBEDDING_DIM:
                logger.warning("Cache corrompido, removendo")
                db.delete(row)
                db.commit()
                return None

            return normalized

        except Exception as exc:
            logger.warning(f"Erro ao buscar cache: {exc}")
            return None
        finally:
            db.close()

    async def cache_embedding(self, query_text: str, embedding: List[float]) -> None:
        """Salva embedding no cache"""
        normalized = _normalize_embedding(embedding)
        if len(normalized) != EMBEDDING_DIM:
            logger.error("Tentativa de cachear embedding inválido")
            return

        text_hash = self._compute_hash(query_text)
        db = SessionLocal()
        try:
            exists = db.execute(
                select(QueryEmbeddingCache).where(
                    QueryEmbeddingCache.query_hash == text_hash
                )
            ).scalar_one_or_none()

            if exists:
                return

            record = QueryEmbeddingCache(
                query_text=query_text[:500],
                query_hash=text_hash,
                embedding=normalized
            )
            db.add(record)
            db.commit()

        except IntegrityError:
            db.rollback()
        except Exception as exc:
            logger.warning(f"Erro ao cachear: {exc}")
            db.rollback()
        finally:
            db.close()

    async def get_query_embedding(self, query: str) -> List[float]:
        """Obtém embedding com fallback para cache"""
        if not query or not query.strip():
            return [0.0] * EMBEDDING_DIM

        cached = await self.get_cached_embedding(query)
        if cached:
            logger.debug("Cache hit")
            return cached

        logger.debug("Cache miss, gerando embedding")
        embedding = await self.generate_embedding(query)

        asyncio.create_task(self.cache_embedding(query, embedding))

        return embedding


embedding_service = EmbeddingService()


async def find_similar_politicians(
    query: str,
    limit: int = 3,
    threshold: float = SIMILARITY_THRESHOLD
) -> List[Dict[str, Any]]:
    """Busca políticos similares por embedding"""
    try:
        query_embedding = await embedding_service.get_query_embedding(query)

        if len(query_embedding) != EMBEDDING_DIM:
            logger.error("Query embedding inválido")
            return []

        db = SessionLocal()
        try:
            qparam = bindparam("q_emb", type_=VectorType(EMBEDDING_DIM))
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
                    sim_expr > threshold,
                )
                .order_by(sim_expr.desc())
                .limit(limit)
            )

            result = db.execute(stmt, {"q_emb": query_embedding}).mappings().all()
            logger.debug(f"Encontrados {len(result)} políticos")
            return [dict(row) for row in result]

        finally:
            db.close()

    except Exception as exc:
        logger.exception(f"Erro na busca por políticos: {exc}")
        return []


async def find_similar_documents(
    query: str,
    limit: int = 5,
    threshold: float = SIMILARITY_THRESHOLD - 0.1
) -> List[Dict[str, Any]]:
    """Busca documentos similares por embedding"""
    try:
        query_embedding = await embedding_service.get_query_embedding(query)

        if len(query_embedding) != EMBEDDING_DIM:
            logger.error("Query embedding inválido")
            return []

        db = SessionLocal()
        try:
            qparam = bindparam("q_emb", type_=VectorType(EMBEDDING_DIM))

            sim_title = func.coalesce(
                1 - DocumentoPolitico.embedding_titulo.op("<=>")(qparam), 0
            )
            sim_ementa = func.coalesce(
                1 - DocumentoPolitico.embedding_ementa.op("<=>")(qparam), 0
            )
            sim_doc = func.coalesce(
                1 - DocumentoPolitico.embedding_documento.op("<=>")(qparam), 0
            )
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
                    max_similarity > threshold,
                )
                .order_by(max_similarity.desc())
                .limit(limit)
            )

            result = db.execute(stmt, {"q_emb": query_embedding}).mappings().all()
            logger.debug(f"Encontrados {len(result)} documentos")
            return [dict(row) for row in result]

        finally:
            db.close()

    except Exception as exc:
        logger.exception(f"Erro na busca por documentos: {exc}")
        return []


async def update_politician_embeddings(batch_size: int = 10, force: bool = False) -> int:
    """Atualiza embeddings de políticos em lote"""
    db = SessionLocal()
    try:
        stmt = select(Politico).where(
            Politico.biografia_resumo.is_not(None),
            Politico.ativo.is_(True)
        ).limit(batch_size)

        rows = db.execute(stmt).scalars().all()
        
        if not rows:
            logger.info("Nenhum político encontrado para atualização")
            return 0
        
        updated = 0
        skipped = 0

        for pol in rows:
            if not pol.biografia_resumo:
                continue

            if not force and pol.embedding_biografia is not None:
                skipped += 1
                continue

            try:
                embedding = await embedding_service.generate_embedding(pol.biografia_resumo)
                if len(embedding) == EMBEDDING_DIM:
                    pol.embedding_biografia = embedding
                    updated += 1
                    logger.debug(f"Embedding atualizado: {pol.nome}")
            except Exception as e:
                logger.error(f"Erro ao processar {pol.nome}: {e}")

        if updated > 0:
            db.commit()
            logger.info(f"Atualizados {updated}/{len(rows)} políticos (pulados: {skipped})")
        else:
            logger.info(f"Processados {len(rows)} políticos, nenhum atualizado (pulados: {skipped})")
        
        return updated

    except Exception as exc:
        logger.error(f"Erro ao atualizar embeddings: {exc}")
        db.rollback()
        return 0
    finally:
        db.close()


async def update_document_embeddings(batch_size: int = 10, force: bool = False) -> int:
    """Atualiza embeddings de documentos em lote"""
    db = SessionLocal()
    try:
        stmt = select(DocumentoPolitico).where(
            DocumentoPolitico.titulo.is_not(None)
        ).limit(batch_size)

        rows = db.execute(stmt).scalars().all()
        
        if not rows:
            logger.info("Nenhum documento encontrado para atualização")
            return 0
        
        updated = 0
        skipped = 0

        for doc in rows:
            doc_updated = False
            
            if not force and (doc.embedding_titulo is not None and 
                             doc.embedding_ementa is not None and 
                             doc.embedding_documento is not None):
                skipped += 1
                continue

            try:
                if doc.titulo and (force or not doc.embedding_titulo):
                    embedding = await embedding_service.generate_embedding(doc.titulo)
                    if len(embedding) == EMBEDDING_DIM:
                        doc.embedding_titulo = embedding
                        doc_updated = True

                if doc.ementa and (force or not doc.embedding_ementa):
                    embedding = await embedding_service.generate_embedding(doc.ementa)
                    if len(embedding) == EMBEDDING_DIM:
                        doc.embedding_ementa = embedding
                        doc_updated = True

                content = doc.conteudo_original or doc.resumo_simplificado
                if content and (force or not doc.embedding_documento):
                    embedding = await embedding_service.generate_embedding(content)
                    if len(embedding) == EMBEDDING_DIM:
                        doc.embedding_documento = embedding
                        doc_updated = True
                
                if doc_updated:
                    updated += 1
                    logger.debug(f"Embeddings atualizados: {doc.titulo[:50]}")

            except Exception as e:
                logger.error(f"Erro ao processar documento {doc.id}: {e}")

        if updated > 0:
            db.commit()
            logger.info(f"Atualizados {updated}/{len(rows)} documentos (pulados: {skipped})")
        else:
            logger.info(f"Processados {len(rows)} documentos, nenhum atualizado (pulados: {skipped})")
        
        return updated

    except Exception as exc:
        logger.error(f"Erro ao atualizar embeddings: {exc}")
        db.rollback()
        return 0
    finally:
        db.close()


async def cleanup_old_cache(days: int = CACHE_TTL_DAYS) -> int:
    """Remove entradas antigas do cache"""
    db = SessionLocal()
    try:
        cutoff = func.now() - func.make_interval(0, 0, 0, days)
        stmt = select(QueryEmbeddingCache).where(
            QueryEmbeddingCache.created_at < cutoff
        )
        old_entries = db.execute(stmt).scalars().all()
        count = len(old_entries)

        for entry in old_entries:
            db.delete(entry)

        db.commit()
        logger.info(f"Removidas {count} entradas antigas do cache")
        return count

    except Exception as exc:
        logger.error(f"Erro ao limpar cache: {exc}")
        db.rollback()
        return 0
    finally:
        db.close()