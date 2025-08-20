"""Modelos Pydantic para Politico."""

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
    nome: str
    partido: Optional[str] = None
    cargo: Optional[CargoEnum] = None

class PoliticoCreate(PoliticoBase):
    """Modelo para inclusão de um novo político."""

class PoliticoUpdate(PoliticoBase):
    """Modelo para atualização de um político."""
    id: int
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

class PoliticoRead(PoliticoBase):
    """Modelo para leitura de um político."""
    id: int
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

