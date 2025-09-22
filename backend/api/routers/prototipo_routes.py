from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.deps import get_session
from backend.services.prototipo_service import PrototipoService
from backend.schemas.prototipo import (
    QuestionarioRequest,
    ResultadoQuestionario,
    PrototipoResponse
)

router = APIRouter(prefix="/prototipo", tags=["Prototipo"])

prototipo_service = PrototipoService()

@router.get("/", response_model=PrototipoResponse)
async def get_votacoes():
    '''Retorna as votações do protótipo'''
    return prototipo_service.get_votacoes_prototipo()

@router.post("/calcular-afinidade", response_model=ResultadoQuestionario)
async def calcular_afinidade(
    request: QuestionarioRequest,
    db: Session = Depends(get_session)
):
    '''Calcula a afinidade do usuário com os deputados'''
    if not request.nome_usuario or not request.nome_usuario.strip():
        raise HTTPException(status_code=400, detail="Nome do usuário é obrigatório.")
    if not request.votos or len(request.votos) == 0:
        raise HTTPException(status_code=400, detail="Votos são obrigatórios.")
    
    votacoes_validas = {1, 2, 3, 4, 5, 6}
    votacoes_recebidas = {voto.votacao_id for voto in request.votos}
    if not votacoes_recebidas.issubset(votacoes_validas):
        raise HTTPException(status_code=400, detail="Votos contêm votações inválidas.")
    votos_validos = {'SIM', 'NAO', 'ABSTENCÃO'}
    for voto in request.votos:
        if voto.voto not in votos_validos:
            raise HTTPException(status_code=400, detail=f"Voto inválido: {voto.voto}. Votos válidos são: {votos_validos}")
    return prototipo_service.calcular_afinidade(db, request)
