"""
Script para atualização de embeddings no sistema
Execute periodicamente para manter embeddings atualizados
"""

from backend.services.embedding_service import (
    update_politician_embeddings, 
    update_document_embeddings,
)

import asyncio
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Executa atualização completa de embeddings"""
    logger.info("Iniciando atualização de embeddings...")
    
    try:
        # Atualiza embeddings de políticos
        logger.info("Atualizando embeddings de políticos...")
        await update_politician_embeddings()
        
        # Atualiza embeddings de documentos
        logger.info("Atualizando embeddings de documentos...")
        await update_document_embeddings()
        
        logger.info("Atualização de embeddings concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante atualização de embeddings: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())