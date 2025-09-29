-- Migration script para adicionar novas colunas e tabelas de embedding
BEGIN;

-- Adiciona novas colunas para embeddings em politicos
ALTER TABLE politicos 
ADD COLUMN IF NOT EXISTS embedding_biografia VECTOR(768),
ADD COLUMN IF NOT EXISTS biografia_resumo TEXT;

-- Adiciona novas colunas para embeddings em documentos_politicos
ALTER TABLE documentos_politicos 
ADD COLUMN IF NOT EXISTS embedding_titulo VECTOR(768),
ADD COLUMN IF NOT EXISTS embedding_ementa VECTOR(768);

-- Cria tabela votos_documento se não existir
CREATE TABLE IF NOT EXISTS votos_documento (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  documento_id UUID NOT NULL REFERENCES documentos_politicos(id) ON DELETE CASCADE,
  politico_id UUID NOT NULL REFERENCES politicos(id) ON DELETE CASCADE,
  voto TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT votos_documento_unq UNIQUE (documento_id, politico_id)
);

-- Cria trigger para votos_documento se não existir
DROP TRIGGER IF EXISTS trg_update_votos_documento ON votos_documento;
CREATE TRIGGER trg_update_votos_documento
BEFORE UPDATE ON votos_documento
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

-- Cria tabela de cache de embeddings de consultas
CREATE TABLE IF NOT EXISTS query_embeddings_cache (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  query_text TEXT NOT NULL,
  query_hash VARCHAR(64) UNIQUE NOT NULL,
  embedding VECTOR(768) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Adiciona novos índices
CREATE INDEX IF NOT EXISTS idx_votos_documento_politico ON votos_documento (politico_id);
CREATE INDEX IF NOT EXISTS idx_votos_documento_documento ON votos_documento (documento_id);
CREATE INDEX IF NOT EXISTS idx_query_embeddings_hash ON query_embeddings_cache (query_hash);

-- Adiciona novos índices vetoriais
CREATE INDEX IF NOT EXISTS politicos_bio_embedding_idx ON politicos USING ivfflat (embedding_biografia vector_l2_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS documentos_titulo_embedding_idx ON documentos_politicos USING ivfflat (embedding_titulo vector_l2_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS documentos_ementa_embedding_idx ON documentos_politicos USING ivfflat (embedding_ementa vector_l2_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS query_embeddings_idx ON query_embeddings_cache USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Atualiza biografias básicas para os políticos existentes
UPDATE politicos SET biografia_resumo = 
  CASE 
    WHEN nome = 'Nikolas Ferreira' THEN 'Deputado Federal por Minas Gerais, PL. Jovem político conservador, conhecido por posições alinhadas ao bolsonarismo.'
    WHEN nome = 'Guilherme Boulos' THEN 'Deputado Federal por São Paulo, PSOL. Coordenador do MTST, ativista social e político de esquerda.'
    WHEN nome = 'Ricardo Salles' THEN 'Deputado Federal por São Paulo, NOVO. Ex-ministro do Meio Ambiente, defende pautas liberais na economia.'
    WHEN nome = 'Tabata Amaral' THEN 'Deputada Federal por São Paulo, PSB. Jovem política, formada por Harvard, foca em educação e políticas públicas.'
    WHEN nome = 'Celso Russomanno' THEN 'Deputado Federal por São Paulo, Republicanos. Jornalista, apresentador, defende direitos do consumidor.'
    WHEN nome = 'Kim Kataguiri' THEN 'Deputado Federal por São Paulo, UNIÃO. Co-fundador do MBL, político liberal.'
    WHEN nome = 'Amom Mandel' THEN 'Deputado Federal por Pernambuco, Cidadania. Empresário e político.'
    WHEN nome = 'Erika Hilton' THEN 'Deputada Federal por São Paulo, PSOL. Primeira mulher trans eleita deputada federal, ativista LGBTQ+.'
    WHEN nome = 'Delegado Palumbo' THEN 'Deputado Federal por São Paulo, MDB. Ex-delegado, foca em segurança pública.'
    WHEN nome = 'Hercílio Coelho Diniz' THEN 'Deputado Federal por Minas Gerais, MDB. Empresário e político.'
    ELSE biografia_resumo
  END
WHERE biografia_resumo IS NULL;

COMMIT;