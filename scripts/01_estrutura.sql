\c iris_db;

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- criando tabelas
CREATE TABLE IF NOT EXISTS politicos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  id_camara BIGINT UNIQUE,
  nome VARCHAR(255) NOT NULL,
  partido VARCHAR(50),
  uf VARCHAR(2),
  cargo VARCHAR(100),
  votos_2022 INTEGER,
  ativo BOOLEAN DEFAULT TRUE,
  ideologia_eco REAL,
  ideologia_soc REAL,
  ideologia_aut REAL,
  ideologia_amb REAL,
  ideologia_est REAL,
  embedding_ideologia VECTOR(768),
  ici REAL,
  historico_ici JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  embedding_biografia VECTOR(768),
  biografia_resumo TEXT
);

CREATE TABLE IF NOT EXISTS documentos_politicos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  id_documento_origem TEXT UNIQUE,
  politico_id UUID REFERENCES politicos(id) ON DELETE SET NULL,
  titulo VARCHAR(500) NOT NULL,
  tipo VARCHAR(50) NOT NULL,
  data_publicacao DATE,
  url_fonte TEXT,
  ementa TEXT,
  conteudo_original TEXT,
  resumo_simplificado TEXT,
  embedding_documento VECTOR(768),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  embedding_titulo VECTOR(768),
  embedding_ementa VECTOR(768)
);

CREATE TABLE IF NOT EXISTS votacoes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  id_votacao_origem TEXT UNIQUE,
  documento_id UUID REFERENCES documentos_politicos(id) ON DELETE SET NULL,
  data_votacao DATE,
  resultado VARCHAR(50) NOT NULL CHECK (resultado IN ('aprovado','rejeitado','em_tramitacao','arquivado')),
  descricao TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS votos_politicos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  votacao_id UUID REFERENCES votacoes(id) ON DELETE CASCADE,
  politico_id UUID REFERENCES politicos(id) ON DELETE CASCADE,
  voto VARCHAR(20) NOT NULL CHECK (voto IN ('sim','nao','abstencao','ausente')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS votacoes_eixo (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  votacao_id UUID REFERENCES votacoes(id) ON DELETE CASCADE,
  eixo TEXT NOT NULL,
  eixo_conf REAL,
  metodo TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS eixo_anchors (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  eixo TEXT NOT NULL,
  polaridade VARCHAR(10) NOT NULL CHECK (polaridade IN ('pos','neg')),
  texto TEXT NOT NULL,
  fonte TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS usuarios_perfis_ideologicos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  data_criacao TIMESTAMPTZ DEFAULT NOW(),
  ideologia_eco REAL,
  ideologia_soc REAL,
  ideologia_aut REAL,
  ideologia_amb REAL,
  ideologia_est REAL,
  embedding_ideologia VECTOR(768),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS votos_documento (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  documento_id UUID NOT NULL REFERENCES documentos_politicos(id) ON DELETE CASCADE,
  politico_id UUID NOT NULL REFERENCES politicos(id) ON DELETE CASCADE,
  voto TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT votos_documento_unq UNIQUE (documento_id, politico_id)
);

CREATE TABLE IF NOT EXISTS query_embeddings_cache (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  query_text TEXT NOT NULL,
  query_hash VARCHAR(64) UNIQUE NOT NULL,
  embedding VECTOR(768) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS response_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id TEXT,
  user_id TEXT,
  prompt TEXT,
  response TEXT,
  sources JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- criando triggers
CREATE TRIGGER trg_update_politicos
  BEFORE UPDATE ON politicos
  FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER trg_update_documentos
  BEFORE UPDATE ON documentos_politicos
  FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER trg_update_votacoes
  BEFORE UPDATE ON votacoes
  FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER trg_update_votos_politicos
  BEFORE UPDATE ON votos_politicos
  FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER trg_update_usuarios_perfis
  BEFORE UPDATE ON usuarios_perfis_ideologicos
  FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER trg_update_votos_documento
  BEFORE UPDATE ON votos_documento
  FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

-- Criar indexes
CREATE UNIQUE INDEX IF NOT EXISTS ux_votacoes_eixo_votacao ON votacoes_eixo(votacao_id);
CREATE INDEX IF NOT EXISTS idx_politicos_id_camara ON politicos (id_camara);
CREATE INDEX IF NOT EXISTS idx_politicos_partido ON politicos (partido);
CREATE INDEX IF NOT EXISTS idx_votos_politicos_votacao ON votos_politicos (votacao_id);
CREATE INDEX IF NOT EXISTS idx_votos_politicos_politico ON votos_politicos (politico_id);
CREATE INDEX IF NOT EXISTS idx_votacoes_id_origem ON votacoes (id_votacao_origem);
CREATE INDEX IF NOT EXISTS idx_documentos_id_origem ON documentos_politicos (id_documento_origem);
CREATE INDEX IF NOT EXISTS idx_politicos_historico_ici ON politicos USING gin (historico_ici);
CREATE INDEX IF NOT EXISTS idx_votos_documento_politico ON votos_documento (politico_id);
CREATE INDEX IF NOT EXISTS idx_votos_documento_documento ON votos_documento (documento_id);
CREATE INDEX IF NOT EXISTS idx_query_embeddings_hash ON query_embeddings_cache (query_hash);
CREATE INDEX IF NOT EXISTS idx_session_messages_session ON session_messages (session_id);
CREATE INDEX IF NOT EXISTS idx_response_log_session ON response_log (session_id);

CREATE INDEX IF NOT EXISTS politicos_embedding_idx ON politicos USING ivfflat (embedding_ideologia vector_l2_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS documentos_embedding_idx ON documentos_politicos USING ivfflat (embedding_documento vector_l2_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS usuarios_embedding_idx ON usuarios_perfis_ideologicos USING ivfflat (embedding_ideologia vector_l2_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS politicos_bio_embedding_idx ON politicos USING ivfflat (embedding_biografia vector_l2_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS documentos_titulo_embedding_idx ON documentos_politicos USING ivfflat (embedding_titulo vector_l2_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS documentos_ementa_embedding_idx ON documentos_politicos USING ivfflat (embedding_ementa vector_l2_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS query_embeddings_idx ON query_embeddings_cache USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);