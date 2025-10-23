"""
Script para atualização de embeddings no sistema
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.services.embedding_service import (
    update_politician_embeddings,
    update_document_embeddings,
    cleanup_old_cache,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Executa atualização completa de embeddings"""
    parser = argparse.ArgumentParser(description='Atualiza embeddings de políticos e documentos')
    parser.add_argument('--batch-size', type=int, default=50, help='Tamanho do lote para processamento')
    parser.add_argument('--skip-politicians', action='store_true', help='Pula atualização de políticos')
    parser.add_argument('--skip-documents', action='store_true', help='Pula atualização de documentos')
    args = parser.parse_args()

    logger.info("Iniciando atualização COMPLETA de embeddings (modo force)")

    try:
        pol_updated = 0
        doc_updated = 0

        if not args.skip_politicians:
            logger.info("Atualizando embeddings de políticos...")
            while True:
                batch_count = await update_politician_embeddings(
                    batch_size=args.batch_size,
                    force=True
                )
                pol_updated += batch_count
                if batch_count == 0:
                    break
                logger.info(f"Processados {pol_updated} políticos até agora...")
        else:
            logger.info("Pulando atualização de políticos")

        if not args.skip_documents:
            logger.info("Atualizando embeddings de documentos...")
            while True:
                batch_count = await update_document_embeddings(
                    batch_size=args.batch_size,
                    force=True
                )
                doc_updated += batch_count
                if batch_count == 0:
                    break
                logger.info(f"Processados {doc_updated} documentos até agora...")
        else:
            logger.info("Pulando atualização de documentos")

        logger.info("Limpando cache antigo...")
        cleaned = await cleanup_old_cache(days=30)

        logger.info(
            f"Atualização concluída! "
            f"Políticos: {pol_updated}, "
            f"Documentos: {doc_updated}, "
            f"Cache limpo: {cleaned}"
        )

    except Exception as e:
        logger.error(f"Erro durante atualização: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())