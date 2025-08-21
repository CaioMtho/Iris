



\c iris_db;

-- Extensões
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- FUNÇÃO DE ATUALIZAÇÃO DE updated_at

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- TABELAS

CREATE TABLE politicos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL,
    partido VARCHAR(50),
    cargo VARCHAR(100),
    ideologia_eco REAL,
    ideologia_soc REAL,
    ideologia_aut REAL,
    ideologia_amb REAL,
    ideologia_est REAL,
    embedding_ideologia VECTOR(768),
    ici REAL,
    historico_ici JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE documentos_politicos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    politico_id UUID REFERENCES politicos(id),
    titulo VARCHAR(500) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    data_publicacao DATE,
    url_fonte TEXT,
    conteudo_original TEXT,
    resumo_simplificado TEXT,
    embedding_documento VECTOR(768),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE votacoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    documento_id UUID REFERENCES documentos_politicos(id),
    data_votacao DATE,
    resultado VARCHAR(50) NOT NULL CHECK (resultado IN ('aprovado','rejeitado','em_tramitacao','arquivado')),
    descricao TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE votos_politicos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    votacao_id UUID REFERENCES votacoes(id),
    politico_id UUID REFERENCES politicos(id),
    voto VARCHAR(20) NOT NULL CHECK (voto IN ('sim','nao','abstencao','ausente')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE incoerencias (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    politico_id UUID REFERENCES politicos(id),
    documento_referencia_id UUID REFERENCES documentos_politicos(id),
    tipo_incoerencia VARCHAR(50) NOT NULL,
    descricao TEXT,
    gravidade VARCHAR(20) NOT NULL CHECK (gravidade IN ('baixa','media','alta','critica')),
    data_deteccao TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE promessas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    politico_id UUID REFERENCES politicos(id),
    descricao TEXT NOT NULL,
    data_promessa DATE,
    viabilidade VARCHAR(20),
    status VARCHAR(50) NOT NULL CHECK (status IN ('pendente','cumprida','em_andamento','nao_cumprida','arquivada')),
    categoria_tematica VARCHAR(100),
    data_cumprimento DATE,
    fontes_verificacao TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE usuarios_perfis_ideologicos (
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

-- TRIGGERS PARA updated_at

CREATE TRIGGER set_timestamp_politicos
BEFORE UPDATE ON politicos
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER set_timestamp_documentos_politicos
BEFORE UPDATE ON documentos_politicos
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER set_timestamp_votacoes
BEFORE UPDATE ON votacoes
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER set_timestamp_votos_politicos
BEFORE UPDATE ON votos_politicos
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER set_timestamp_incoerencias
BEFORE UPDATE ON incoerencias
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER set_timestamp_promessas
BEFORE UPDATE ON promessas
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

CREATE TRIGGER set_timestamp_usuarios_perfis_ideologicos
BEFORE UPDATE ON usuarios_perfis_ideologicos
FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

-- ÍNDICES RECOMENDADOS PARA DESEMPENHO

CREATE INDEX politicos_ideologia_idx ON politicos USING HNSW (embedding_ideologia vector_l2_ops);
CREATE INDEX documentos_politicos_embedding_idx ON documentos_politicos USING HNSW (embedding_documento vector_l2_ops);
CREATE INDEX usuarios_perfis_ideologicos_embedding_idx ON usuarios_perfis_ideologicos USING HNSW (embedding_ideologia vector_l2_ops);

CREATE INDEX votos_politicos_votacao_id_idx ON votos_politicos(votacao_id);
CREATE INDEX votos_politicos_politico_id_idx ON votos_politicos(politico_id);
CREATE INDEX incoerencias_politico_id_idx ON incoerencias(politico_id);
CREATE INDEX promessas_politico_id_idx ON promessas(politico_id);

