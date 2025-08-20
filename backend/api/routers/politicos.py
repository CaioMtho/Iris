from fastapi import APIRouter, HTTPException
from backend.db.db import conectar
from backend.models.politico import PoliticoCreate

router = APIRouter()

@router.get("/")
async def ler_politicos():
    """Lê todos os políticos do banco de dados."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM politicos")
    politicos = cursor.fetchall()
    cursor.close()
    conn.close()
    return politicos

@router.get("/{politico_id}")
async def ler_politico(politico_id: int):
    """Lê um político específico pelo ID."""
    conn = None
    cursor = None
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM politicos WHERE id = %s", (politico_id,))
        politico = cursor.fetchone()
        if politico:
            return politico
        raise HTTPException(status_code=404, detail="Político não encontrado")
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

@router.post("/", status_code=201)
async def criar_politico(politico: PoliticoCreate):
    """Cria um novo político no banco de dados."""
    conn = None
    cursor = None
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO politicos (nome, partido, cargo) VALUES (%s, %s, %s) RETURNING id",
            (politico.nome, politico.partido, politico.cargo)
        )
        result = cursor.fetchone()
        if result is None:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=500, detail="Falha ao criar político")
        politico_id = result[0]
        conn.commit()
        return {"id": politico_id,
                "nome": politico.nome,
                "partido": politico.partido,
                "cargo": politico.cargo}
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
        