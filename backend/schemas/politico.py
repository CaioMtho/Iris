"""Modelos Pydantic para Politico."""

from uuid import UUID
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class CargoEnum(str, Enum):
    """Enum para cargos políticos."""
    DEPUTADO_FEDERAL = "Deputado Federal"
    SENADOR = "Senador"
    GOVERNADOR = "Governador"
    PRESIDENTE = "Presidente"
    DEPUTADO_ESTADUAL = "Deputado Estadual"
    PREFEITO = "Prefeito"
    VEREADOR = "Vereador"

class PoliticoBase(BaseModel):
    """Modelo base para a classe Politico."""
    nome: str = Field(
        max_length=100,
        min_length=1,
        )
    partido: Optional[str] = Field(
        max_length=50,
        min_length=1,)
    cargo: Optional[CargoEnum] = None
    model_config = {
        "from_attributes": True
    }

class PoliticoCreate(PoliticoBase):
    """Modelo para inclusão de um novo político."""
    model_config = {
        "from_attributes": True
    }

class PoliticoUpdate(PoliticoBase):
    """Modelo para atualização de um político."""
    ideologia_eco: Optional[float] = None
    ideologia_soc: Optional[float] = None
    ideologia_aut: Optional[float] = None
    ideologia_amb: Optional[float] = None
    ideologia_est: Optional[float] = None
    embedding_ideologia: Optional[List[float]] = Field(
        default=None, description="Embedding para BERTimbau, 768 dimensões"
    )
    ici: Optional[float] = Field(
        default=None,
        description="Indice de Coerência Ideológica"
    )
    historico_ici: Optional[Dict[str, float]] = Field(
        default=None,
        description="Historico do ICI, com data como chave"
    )
    
    model_config = {
        "from_attributes": True
    }

class PoliticoRead(PoliticoBase):
    """Modelo para leitura de um político."""
    id: UUID
    ideologia_eco: Optional[float] = None
    ideologia_soc: Optional[float] = None
    ideologia_aut: Optional[float] = None
    ideologia_amb: Optional[float] = None
    ideologia_est: Optional[float] = None
    embedding_ideologia: Optional[List[float]] = Field(
        default=None,
        description="Embedding para BERTimbau, 768 dimensões"
    )
    ici: Optional[float] = Field(
        default=None,
        description="Indice de Coerência Ideológica"
    )
    historico_ici: Optional[Dict[str, float]] = Field(
        default=None,
        description="Historico do ICI, com data como chave"
    )
    model_config = {
        "from_attributes": True
    }

class PoliticoStats(BaseModel):
    """Modelo para estatísticas de políticos."""
    total_politicos: int = Field(description="Total de políticos cadastrados")
    por_partido: Dict[str, int] = Field(description="Contagem de políticos por partido")
    por_cargo: Dict[str, int] = Field(description="Contagem de políticos por cargo")
    ici_medio: Optional[float] = Field(description="Média do Índice de Coerência Ideológica (ICI)")
    model_config = {
        "from_attributes": True
    }