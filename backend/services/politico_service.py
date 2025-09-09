import logging
from uuid import UUID
from typing import List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.schemas.politico import PoliticoCreate, PoliticoUpdate, PoliticoRead
from backend.models.politico import Politico

logger = logging.getLogger(__name__)


class PoliticoService:
    """Serviço para políticos usando SQLAlchemy."""

    @staticmethod
    def _to_read(p: Politico) -> PoliticoRead:
        """Converte ORM -> Pydantic"""
        return PoliticoRead.model_validate(p)

    @staticmethod
    def listar_politicos(db: Session) -> List[PoliticoRead]:
        try:
            politicos = db.query(Politico).order_by(Politico.nome).all()
            return [PoliticoService._to_read(p) for p in politicos]
        except SQLAlchemyError as e:
            logger.error("Erro ao listar políticos: %s", str(e))
            raise HTTPException(500, "Erro interno ao buscar políticos") from e

    @staticmethod
    def buscar_politico_por_id(db: Session, politico_id: UUID) -> Optional[PoliticoRead]:
        try:
            p = db.query(Politico).filter(Politico.id == politico_id).first()
            return PoliticoService._to_read(p) if p else None
        except SQLAlchemyError as e:
            logger.error("Erro ao buscar político %s: %s", politico_id, str(e))
            raise HTTPException(500, "Erro interno ao buscar político") from e

    @staticmethod
    def criar_politico(db: Session, politico: PoliticoCreate) -> PoliticoRead:
        if not politico.nome or not politico.partido or not politico.cargo:
            raise HTTPException(400, "Nome, partido e cargo são obrigatórios")

        try:
            novo = Politico(
                nome=politico.nome.strip(),
                partido=politico.partido.strip(),
                cargo=politico.cargo,
            )
            db.add(novo)
            db.commit()
            db.refresh(novo)
            return PoliticoService._to_read(novo)
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Erro ao criar político: %s", str(e))
            raise HTTPException(500, "Erro interno ao criar político") from e

    @staticmethod
    def atualizar_politico(db: Session, politico_id: UUID, politico: PoliticoUpdate) -> PoliticoRead:
        p = db.query(Politico).filter(Politico.id == politico_id).first()
        if not p:
            raise HTTPException(404, "Político não encontrado")

        try:
            for campo, valor in politico.dict(exclude_unset=True, exclude={'id'}).items():
                setattr(p, campo, valor)
            db.commit()
            db.refresh(p)
            return PoliticoService._to_read(p)
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Erro ao atualizar político %s: %s", politico_id, str(e))
            raise HTTPException(500, "Erro interno ao atualizar político") from e

    @staticmethod
    def criar_ou_atualizar_politico(
        db: Session, politico_id: UUID, politico: PoliticoUpdate
    ) -> Tuple[PoliticoRead, bool]:
        existente = db.query(Politico).filter(Politico.id == politico_id).first()
        if existente:
            atualizado = PoliticoService.atualizar_politico(db, politico_id, politico)
            return atualizado, False

        if not politico.nome or not politico.partido or not politico.cargo:
            raise HTTPException(400, "Nome, partido e cargo são obrigatórios para criação")

        criado = PoliticoService.criar_politico(db, PoliticoCreate(**politico.dict()))
        return criado, True

    @staticmethod
    def deletar_politico(db: Session, politico_id: UUID) -> bool:
        p = db.query(Politico).filter(Politico.id == politico_id).first()
        if not p:
            raise HTTPException(404, "Político não encontrado")
        try:
            db.delete(p)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Erro ao deletar político %s: %s", politico_id, str(e))
            raise HTTPException(500, "Erro interno ao deletar político") from e

    @staticmethod
    def buscar_politicos_por_partido(db: Session, partido: str) -> List[PoliticoRead]:
        if not partido or not partido.strip():
            raise HTTPException(400, "Partido é obrigatório")

        try:
            politicos = (
                db.query(Politico)
                .filter(Politico.partido.ilike(partido.strip()))
                .order_by(Politico.nome)
                .all()
            )
            return [PoliticoService._to_read(p) for p in politicos]
        except SQLAlchemyError as e:
            logger.error("Erro ao buscar políticos do partido %s: %s", partido, str(e))
            raise HTTPException(500, "Erro interno ao buscar políticos por partido") from e