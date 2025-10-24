from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.deps import get_session
from backend.models.models import DadosQuestionario

router = APIRouter()

@router.post("/dados_questionarios")
async def salvar_dados_questionario(request: Request, db: Session = Depends(get_session)):
    try:
        payload = await request.json()

        input = payload.get("input")
        output = payload.get("output")

        if not input or not output:
            raise HTTPException(status_code=400, detail="Campos 'input' e 'output' são obrigatórios.")

        dados = DadosQuestionario(
            input=input,
            output=output
        )
        db.add(dados)
        db.commit()
        db.refresh(dados)

        return {"id": str(dados.id), "created_at": dados.created_at}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar questionário: {str(e)}")
