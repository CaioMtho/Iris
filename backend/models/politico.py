"""Modelo de dados para políticos"""
import uuid
from sqlalchemy import Column, String, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from backend.db.database import Base

class Politico(Base):
    """Modelo de dados para a tabela de políticos"""
    __tablename__ = "politicos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False)
    partido = Column(String, nullable=False)
    cargo = Column(String, nullable=False)
    ideologia_eco = Column(Float, nullable=True)
    ideologia_soc = Column(Float, nullable=True)
    ideologia_aut = Column(Float, nullable=True)
    ideologia_amb = Column(Float, nullable=True)
    ideologia_est = Column(Float, nullable=True)
    embedding_ideologia = Column(JSON, nullable=True)
    ici = Column(Float, nullable=True)
    historico_ici = Column(JSON, nullable=True)
