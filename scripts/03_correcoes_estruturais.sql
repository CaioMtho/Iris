

\c iris_db;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='politicos' AND column_name='embedding_updated_at'
    ) THEN
        ALTER TABLE politicos ADD COLUMN embedding_updated_at TIMESTAMPTZ;
        COMMENT ON COLUMN politicos.embedding_updated_at IS 'Última atualização do embedding de biografia';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='documentos_politicos' AND column_name='embedding_updated_at'
    ) THEN
        ALTER TABLE documentos_politicos ADD COLUMN embedding_updated_at TIMESTAMPTZ;
        COMMENT ON COLUMN documentos_politicos.embedding_updated_at IS 'Última atualização dos embeddings';
    END IF;
END $$;

-- Adiciona índices para otimizar queries de atualização
CREATE INDEX IF NOT EXISTS idx_politicos_embedding_updated 
    ON politicos (embedding_updated_at) 
    WHERE embedding_biografia IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documentos_embedding_updated 
    ON documentos_politicos (embedding_updated_at) 
    WHERE embedding_documento IS NOT NULL;

-- Adiciona índice composto para queries de busca
CREATE INDEX IF NOT EXISTS idx_politicos_active_with_bio 
    ON politicos (ativo, biografia_resumo) 
    WHERE biografia_resumo IS NOT NULL;

-- Índice para otimizar queries de documentos pendentes
CREATE INDEX IF NOT EXISTS idx_documentos_pending_embeddings 
    ON documentos_politicos (titulo) 
    WHERE embedding_titulo IS NULL 
       OR embedding_ementa IS NULL 
       OR embedding_documento IS NULL;

-- View para monitoramento de embeddings
CREATE OR REPLACE VIEW v_embedding_status AS
SELECT 
    'politicos' AS tabela,
    COUNT(*) AS total,
    COUNT(embedding_biografia) AS com_embedding,
    COUNT(*) - COUNT(embedding_biografia) AS sem_embedding,
    ROUND(100.0 * COUNT(embedding_biografia) / NULLIF(COUNT(*), 0), 2) AS percentual_completo
FROM politicos
WHERE ativo = TRUE AND biografia_resumo IS NOT NULL

UNION ALL

SELECT 
    'documentos' AS tabela,
    COUNT(*) AS total,
    COUNT(CASE WHEN embedding_titulo IS NOT NULL 
               AND embedding_ementa IS NOT NULL 
               AND embedding_documento IS NOT NULL 
          THEN 1 END) AS com_embedding,
    COUNT(CASE WHEN embedding_titulo IS NULL 
               OR embedding_ementa IS NULL 
               OR embedding_documento IS NULL 
          THEN 1 END) AS sem_embedding,
    ROUND(100.0 * COUNT(CASE WHEN embedding_titulo IS NOT NULL 
                              AND embedding_ementa IS NOT NULL 
                              AND embedding_documento IS NOT NULL 
                         THEN 1 END) / NULLIF(COUNT(*), 0), 2) AS percentual_completo
FROM documentos_politicos
WHERE titulo IS NOT NULL;

-- Função para verificar integridade de embeddings
CREATE OR REPLACE FUNCTION check_embedding_integrity()
RETURNS TABLE(
    tabela TEXT,
    id UUID,
    problema TEXT
) AS $$
BEGIN
    -- Verifica políticos com biografia mas sem embedding
    RETURN QUERY
    SELECT 
        'politicos'::TEXT,
        p.id,
        'Biografia presente mas sem embedding'::TEXT
    FROM politicos p
    WHERE p.ativo = TRUE 
      AND p.biografia_resumo IS NOT NULL 
      AND p.embedding_biografia IS NULL;
    
    -- Verifica documentos com dados mas embeddings incompletos
    RETURN QUERY
    SELECT 
        'documentos'::TEXT,
        d.id,
        'Título sem embedding'::TEXT
    FROM documentos_politicos d
    WHERE d.titulo IS NOT NULL 
      AND d.embedding_titulo IS NULL;
    
    RETURN QUERY
    SELECT 
        'documentos'::TEXT,
        d.id,
        'Ementa sem embedding'::TEXT
    FROM documentos_politicos d
    WHERE d.ementa IS NOT NULL 
      AND d.embedding_ementa IS NULL;
    
    RETURN QUERY
    SELECT 
        'documentos'::TEXT,
        d.id,
        'Conteúdo sem embedding'::TEXT
    FROM documentos_politicos d
    WHERE (d.conteudo_original IS NOT NULL OR d.resumo_simplificado IS NOT NULL)
      AND d.embedding_documento IS NULL;
END;
$$ LANGUAGE plpgsql;

COMMIT;