"""Serviços para Político."""
import logging
from uuid import UUID
from typing import List, Optional, Dict, Any
from psycopg2.extras import Json, RealDictCursor
from fastapi import HTTPException

from backend.db.db import conectar
from backend.models.politico import PoliticoCreate, PoliticoUpdate, PoliticoRead

logger = logging.getLogger(__name__)


class PoliticoService:
    """Serviço para políticos."""

    @staticmethod
    def _dict_to_politico_read(row: Dict[str, Any]) -> PoliticoRead:
        """Converte um dicionário do banco para PoliticoRead."""
        return PoliticoRead(
            id=row['id'],
            nome=row['nome'],
            partido=row.get('partido'),
            cargo=row.get('cargo'),
            ideologia_eco=row.get('ideologia_eco'),
            ideologia_soc=row.get('ideologia_soc'),
            ideologia_aut=row.get('ideologia_aut'),
            ideologia_amb=row.get('ideologia_amb'),
            ideologia_est=row.get('ideologia_est'),
            embedding_ideologia=row.get('embedding_ideologia'),
            ici=row.get('ici'),
            historico_ici=row.get('historico_ici')
        )

    @staticmethod
    def _validate_politico_create(politico: PoliticoCreate) -> None:
        """Valida dados obrigatórios para criação de político."""
        if not politico.nome or not politico.nome.strip():
            raise HTTPException(
                status_code=400,
                detail="Nome é obrigatório e não pode estar vazio"
            )
        if not politico.partido or not politico.partido.strip():
            raise HTTPException(
                status_code=400,
                detail="Partido é obrigatório e não pode estar vazio"
            )
        if not politico.cargo:
            raise HTTPException(
                status_code=400,
                detail="Cargo é obrigatório"
            )

    @staticmethod
    def listar_politicos() -> List[PoliticoRead]:
        """Lista todos os políticos."""
        try:
            with conectar() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, nome, partido, cargo, ideologia_eco, ideologia_soc,
                               ideologia_aut, ideologia_amb, ideologia_est,
                               embedding_ideologia, ici, historico_ici
                        FROM politicos
                        ORDER BY nome
                    """)
                    rows = cursor.fetchall()
                    return [PoliticoService._dict_to_politico_read(row) for row in rows]
        except Exception as e:
            logger.error("Erro ao listar políticos: %s", str(e))
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao buscar políticos"
            ) from e

    @staticmethod
    def buscar_politico_por_id(politico_id: UUID) -> Optional[PoliticoRead]:
        """Busca um político por ID."""
        try:
            with conectar() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, nome, partido, cargo, ideologia_eco, ideologia_soc,
                               ideologia_aut, ideologia_amb, ideologia_est,
                               embedding_ideologia, ici, historico_ici
                        FROM politicos
                        WHERE id = %s
                    """, (str(politico_id),))
                    row = cursor.fetchone()
                    if row:
                        return PoliticoService._dict_to_politico_read(row)
                    return None
        except Exception as e:
            logger.error("Erro ao buscar político ID %s: %s", politico_id, str(e))
            raise HTTPException(
                status_code=500,
                detail="Erro interno do servidor ao buscar político"
            ) from e

    @staticmethod
    def criar_politico(politico: PoliticoCreate) -> PoliticoRead:
        """Cria um novo político."""
        PoliticoService._validate_politico_create(politico)

        try:
            with conectar() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        INSERT INTO politicos (nome, partido, cargo)
                        VALUES (%s, %s, %s)
                        RETURNING id, nome, partido, cargo, ideologia_eco, ideologia_soc,
                                  ideologia_aut, ideologia_amb, ideologia_est,
                                  embedding_ideologia, ici, historico_ici
                    """, (
                        politico.nome.strip() if politico.nome else None,
                        politico.partido.strip() if politico.partido else None,
                        politico.cargo
                    ))

                    row = cursor.fetchone()
                    if not row:
                        raise HTTPException(
                            status_code=500,
                            detail="Falha ao criar político"
                        )

                    conn.commit()
                    return PoliticoService._dict_to_politico_read(row)

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Erro ao criar político: %s", str(e))
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao criar político"
            ) from e

    @staticmethod
    def atualizar_politico(politico_id: UUID, politico: PoliticoUpdate) -> PoliticoRead:
        """Atualiza um político existente."""

        # Verifica se o político existe
        politico_existente = PoliticoService.buscar_politico_por_id(politico_id)
        if not politico_existente:
            raise HTTPException(
                status_code=404,
                detail="Político não encontrado"
            )

        try:
            with conectar() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Monta dinamicamente os campos a serem atualizados
                    update_fields = []
                    values = []

                    data_dict = politico.dict(exclude_unset=True, exclude={'id'})

                    for campo, valor in data_dict.items():
                        if valor is not None:
                            if campo == "historico_ici":
                                update_fields.append(f"{campo} = %s")
                                values.append(Json(valor))
                            elif campo in ["nome", "partido"] and isinstance(valor, str):
                                update_fields.append(f"{campo} = %s")
                                values.append(valor.strip())
                            else:
                                update_fields.append(f"{campo} = %s")
                                values.append(valor)

                    if not update_fields:
                        # retorna o político atual se não tiver nenhum campo
                        return politico_existente

                    sql = f"""
                        UPDATE politicos 
                        SET {', '.join(update_fields)}
                        WHERE id = %s
                        RETURNING id, nome, partido, cargo, ideologia_eco, ideologia_soc,
                                  ideologia_aut, ideologia_amb, ideologia_est,
                                  embedding_ideologia, ici, historico_ici
                    """
                    values.append(str(politico_id))

                    cursor.execute(sql, tuple(values))
                    row = cursor.fetchone()

                    if not row:
                        raise HTTPException(
                            status_code=500,
                            detail="Falha ao atualizar político"
                        )

                    conn.commit()
                    return PoliticoService._dict_to_politico_read(row)

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Erro ao atualizar político ID %i: %s", politico_id, str(e))
            raise HTTPException(
                status_code=500,
                detail="Erro interno do servidor ao atualizar político"
            ) from e

    @staticmethod
    def criar_ou_atualizar_politico(politico_id: UUID, politico: PoliticoUpdate) -> tuple[PoliticoRead, bool]:
        """
        Cria ou atualiza um político (operação upsert).
        
        Returns:
            tuple: (PoliticoRead, bool) bool indica se foi criado (True) ou atualizado (False)
        """

        # Verifica se existe
        politico_existente = PoliticoService.buscar_politico_por_id(politico_id)

        if politico_existente:
            politico_atualizado = PoliticoService.atualizar_politico(politico_id, politico)
            return politico_atualizado, False

        # Cria novo
        if not politico.nome or not politico.partido or not politico.cargo:
            raise HTTPException(
                status_code=400,
                detail="Para criar um político novo, nome, partido e cargo são obrigatórios"
            )

        criado = PoliticoService.criar_politico(PoliticoCreate(
            nome=politico.nome,
            partido=politico.partido,
            cargo=politico.cargo))
        return criado, True

    @staticmethod
    def deletar_politico(politico_id: UUID) -> bool:
        """
        Deleta um político por ID.
        
        Returns:
            bool: True se deletado com sucesso
        """

        try:
            with conectar() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM politicos WHERE id = %s", (str(politico_id),))

                    if cursor.rowcount == 0:
                        raise HTTPException(
                            status_code=404,
                            detail="Político não encontrado"
                        )

                    conn.commit()
                    return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Erro ao deletar político ID %s: %s", politico_id, str(e))
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao deletar político"
            ) from e

    @staticmethod
    def buscar_politicos_por_partido(partido: str) -> List[PoliticoRead]:
        """Busca políticos por partido."""
        if not partido or not partido.strip():
            raise HTTPException(
                status_code=400,
                detail="Nome do partido é obrigatório"
            )

        try:
            with conectar() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, nome, partido, cargo, ideologia_eco, ideologia_soc,
                               ideologia_aut, ideologia_amb, ideologia_est,
                               embedding_ideologia, ici, historico_ici
                        FROM politicos
                        WHERE UPPER(partido) = UPPER(%s)
                        ORDER BY nome
                    """, (partido.strip(),))

                    rows = cursor.fetchall()
                    return [PoliticoService._dict_to_politico_read(row) for row in rows]

        except Exception as e:
            logger.error("Erro ao buscar políticos do partido %s: %s", partido, str(e))
            raise HTTPException(
                status_code=500,
                detail="Erro interno do servidor ao buscar políticos por partido"
            ) from e
