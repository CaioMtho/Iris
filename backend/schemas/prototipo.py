'''Modelos de dados para o protótipo'''

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class VotoEscolha(BaseModel):
    '''Escolha de voto do usuário'''
    votacao_id: int
    voto: str

class QuestionarioRequest(BaseModel):
    '''Request do usuário com suas escolhas'''
    nome_usuario: str
    votos: List[VotoEscolha]

class DeputadoAfinidade(BaseModel):
    '''Resultado de afinidade com um deputado'''
    id: UUID
    nome: str
    partido: str
    uf: Optional[str] = None
    afinidade_percentual: float
    votos_coincidentes: int
    votos_divergentes: int
    votacoes_comparaveis: int
    detalhes: Dict[str, Any]
    
class ResultadoQuestionario(BaseModel):
    '''Resultado do questionário de afinidade'''
    nome_usuario: str
    data_realizacao: datetime
    ranking_afinidade: List[DeputadoAfinidade]
    resumo_estatistico: Dict[str, Any]
    
class VotacaoInfo(BaseModel):
    '''Informações sobre uma votação'''
    id: int
    ordem: int
    titulo: str
    resumo: str
    contexto_atual: str
    mudancas_propostas: str
    argumentos_favor: List[str]
    argumentos_contra: List[str]
    
class PrototipoResponse(BaseModel):
    '''Response com dados do protótipo'''
    votacoes : List[VotacaoInfo]
    total_votacoes : int
    