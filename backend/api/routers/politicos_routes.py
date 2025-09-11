"""Endpoints de políticos."""
from uuid import UUID
import logging
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from backend.db.deps import get_session

from backend.schemas.politico import PoliticoCreate, PoliticoUpdate, PoliticoRead
from backend.services.politico_service import PoliticoService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/politicos", tags=["políticos"])


@router.get(
    "/",
    response_model=List[PoliticoRead],
    summary="Lista todos os políticos",
    description="Retorna uma lista com todos os políticos cadastrados no sistema."
)
async def listar_politicos(db: Session = Depends(get_session)) -> List[PoliticoRead]:
    """Lista todos os políticos cadastrados."""
    logger.info("Listando todos os políticos")
    return PoliticoService.listar_politicos(db)


@router.get(
    "/{politico_id}",
    response_model=PoliticoRead,
    summary="Busca político por ID",
    description="Retorna os dados de um político específico pelo seu ID.",
    responses={
        404: {"description": "Político não encontrado"},
        400: {"description": "ID inválido"}
    }
)
async def buscar_politico(politico_id: UUID, db: Session = Depends(get_session)) -> PoliticoRead:
    """Busca um político específico pelo ID."""
    logger.info("Buscando político com ID: %s", politico_id)

    politico = PoliticoService.buscar_politico_por_id(db, politico_id)
    if not politico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Político não encontrado"
        )

    return politico


@router.post(
    "/",
    response_model=PoliticoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria novo político",
    description="Cria um novo político no sistema com os dados fornecidos.",
    responses={
        400: {"description": "Dados inválidos ou obrigatórios não fornecidos"},
        201: {"description": "Político criado com sucesso"}
    }
)
async def criar_politico( politico: PoliticoCreate, db : Session = Depends(get_session)) -> PoliticoRead:
    """Cria um novo político no banco de dados."""
    logger.info("Criando novo político: %s", politico.nome)
    return PoliticoService.criar_politico(db, politico)

@router.put(
    "/{politico_id}",
    response_model=PoliticoRead,
    summary="Atualiza político existente",
    description="Atualiza os dados de um político existente pelo ID.",
    responses={
        404: {"description": "Político não encontrado"},
        400: {"description": "ID ou dados inválidos"},
        200: {"description": "Político atualizado com sucesso"}
    }
)
async def atualizar_politico(politico_id: UUID, politico: PoliticoUpdate, db : Session = Depends(get_session)) -> PoliticoRead:
    """Atualiza um político existente pelo ID."""
    logger.info("Atualizando político ID: %s", politico_id)
    return PoliticoService.atualizar_politico(db, politico_id, politico)


@router.patch(
    "/{politico_id}",
    response_model=PoliticoRead,
    summary="Cria ou atualiza político",
    description="Cria um novo político com o ID especificado ou atualiza se já existir.",
    responses={
        200: {"description": "Político atualizado com sucesso"},
        201: {"description": "Político criado com sucesso"},
        400: {"description": "ID ou dados inválidos"}
    }
)
async def upsert_politico(politico_id: UUID, politico: PoliticoUpdate, db : Session = Depends(get_session)) -> PoliticoRead:
    """Cria ou atualiza um político (operação upsert)."""
    logger.info("Operação upsert para político ID: %s", politico_id)

    politico_resultado, foi_criado = PoliticoService.criar_ou_atualizar_politico(
        db, politico_id, politico
    )

    if foi_criado:
        logger.info("Político criado com ID: %s", politico_id)
    else:
        logger.info("Político atualizado com ID: %s", politico_id)

    return politico_resultado


@router.delete(
    "/{politico_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove político",
    description="Remove um político do sistema pelo seu ID.",
    responses={
        404: {"description": "Político não encontrado"},
        400: {"description": "ID inválido"},
        204: {"description": "Político removido com sucesso"}
    }
)
async def deletar_politico(politico_id: UUID, db : Session = Depends(get_session)) -> Response:
    """Remove um político pelo ID."""
    logger.info("Deletando político ID: %s", politico_id)

    PoliticoService.deletar_politico(db, politico_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/partido/{partido}",
    response_model=List[PoliticoRead],
    summary="Lista políticos por partido",
    description="Retorna todos os políticos de um partido específico.",
    responses={
        400: {"description": "Nome do partido inválido"},
        200: {"description": "Lista de políticos do partido"}
    }
)
async def listar_politicos_por_partido(partido: str, db : Session = Depends(get_session)) -> List[PoliticoRead]:
    """Lista políticos de um partido específico."""
    logger.info("Listando políticos do partido: %s", partido)
    return PoliticoService.buscar_politicos_por_partido(db, partido)
