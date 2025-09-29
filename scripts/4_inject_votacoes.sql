CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

BEGIN;

WITH proto(nome, id_camara, id_uuid, biografia) AS (
VALUES
('Nikolas Ferreira', 209787, '470a3d7c-de66-432b-8496-7f192bc1036c'::uuid, 'Deputado Federal por Minas Gerais, PL. Jovem político conservador, conhecido por posições alinhadas ao bolsonarismo.'),
('Guilherme Boulos', 220639, 'a6e54a4d-31f9-4afb-9679-ea2f1e23dd88'::uuid, 'Deputado Federal por São Paulo, PSOL. Coordenador do MTST, ativista social e político de esquerda.'),
('Ricardo Salles', 220633, '09d41dd7-a991-41c8-9750-2998117965dc'::uuid, 'Deputado Federal por São Paulo, NOVO. Ex-ministro do Meio Ambiente, defende pautas liberais na economia.'),
('Tabata Amaral', 204534, '8c6a4a08-a3ef-44d2-9c5f-452374438c5f'::uuid, 'Deputada Federal por São Paulo, PSB. Jovem política, formada por Harvard, foca em educação e políticas públicas.'),
('Celso Russomanno', 73441, '070bb287-2cb8-4f72-984d-359ea7d670b0'::uuid, 'Deputado Federal por São Paulo, Republicanos. Jornalista, apresentador, defende direitos do consumidor.'),
('Kim Kataguiri', 204536, '09beda65-18c8-4120-919f-15f51a4e543b'::uuid, 'Deputado Federal por São Paulo, UNIÃO. Co-fundador do MBL, político liberal.'),
('Amom Mandel', 220715, '98dd4786-666a-4f13-837e-208d94739ce6'::uuid, 'Deputado Federal por Pernambuco, Cidadania. Empresário e político.'),
('Erika Hilton', 220645, '816fdbd3-4830-4eae-9cd5-9b5949166037'::uuid, 'Deputada Federal por São Paulo, PSOL. Primeira mulher trans eleita deputada federal, ativista LGBTQ+.'),
('Delegado Palumbo', 220652, '80d6c6db-b15b-4ee5-95c0-94c167340da3'::uuid, 'Deputado Federal por São Paulo, MDB. Ex-delegado, foca em segurança pública.'),
('Hercílio Coelho Diniz', 204539, 'b2b636ed-780e-4b56-a072-b6f6e7115fba'::uuid, 'Deputado Federal por Minas Gerais, MDB. Empresário e político.')
)
INSERT INTO politicos (id, id_camara, nome, partido, uf, cargo, ativo, biografia_resumo, created_at, updated_at)
SELECT
COALESCE(id_uuid, uuid_generate_v4()) AS id,
id_camara,
nome,
CASE nome
WHEN 'Nikolas Ferreira' THEN 'PL'
WHEN 'Guilherme Boulos' THEN 'PSOL'
WHEN 'Ricardo Salles' THEN 'NOVO'
WHEN 'Tabata Amaral' THEN 'PSB'
WHEN 'Celso Russomanno' THEN 'Republicanos'
WHEN 'Kim Kataguiri' THEN 'UNIÃO'
WHEN 'Amom Mandel' THEN 'Cidadania'
WHEN 'Erika Hilton' THEN 'PSOL'
WHEN 'Delegado Palumbo' THEN 'MDB'
WHEN 'Hercílio Coelho Diniz' THEN 'MDB'
ELSE 'DESCONHECIDO'
END AS partido,
CASE nome
WHEN 'Nikolas Ferreira' THEN 'MG'
WHEN 'Guilherme Boulos' THEN 'SP'
WHEN 'Ricardo Salles' THEN 'SP'
WHEN 'Tabata Amaral' THEN 'SP'
WHEN 'Celso Russomanno' THEN 'SP'
WHEN 'Kim Kataguiri' THEN 'SP'
WHEN 'Amom Mandel' THEN 'PE'
WHEN 'Erika Hilton' THEN 'SP'
WHEN 'Delegado Palumbo' THEN 'SP'
WHEN 'Hercílio Coelho Diniz' THEN 'MG'
ELSE NULL
END AS uf,
'Deputado Federal' AS cargo,
TRUE AS ativo,
biografia,
NOW() AS created_at,
NOW() AS updated_at
FROM proto
ON CONFLICT (id_camara) DO UPDATE
SET nome = EXCLUDED.nome,
partido = EXCLUDED.partido,
uf = EXCLUDED.uf,
cargo = EXCLUDED.cargo,
biografia_resumo = EXCLUDED.biografia_resumo,
updated_at = NOW();

COMMIT;

BEGIN;

CREATE TABLE IF NOT EXISTS votos_documento (
id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
documento_id UUID NOT NULL REFERENCES documentos_politicos(id) ON DELETE CASCADE,
politico_id UUID NOT NULL REFERENCES politicos(id) ON DELETE CASCADE,
voto TEXT NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
CONSTRAINT votos_documento_unq UNIQUE (documento_id, politico_id)
);

COMMIT;

BEGIN;

INSERT INTO documentos_politicos (id_documento_origem, titulo, tipo, data_publicacao, url_fonte, ementa, conteudo_original, resumo_simplificado, created_at, updated_at)
VALUES
('votacao-1',
'Marco Temporal das Terras Indígenas (PL 490/2007)',
'votacao',
NULL,
NULL,
'Projeto que estabelece que só podem ser demarcadas como terras indígenas áreas ocupadas até 05/10/1988. Aprovado na Câmara em maio de 2023; polêmica entre ruralistas e indigenistas.',
'Projeto que estabelece que só podem ser demarcadas como terras indígenas áreas ocupadas até 05/10/1988. Aprovado na Câmara em maio de 2023; polêmica entre ruralistas e indigenistas.',
'Projeto que estabelece que só podem ser demarcadas como terras indígenas... (resumo)',
NOW(),
NOW()
)
ON CONFLICT (id_documento_origem) DO UPDATE
SET titulo = EXCLUDED.titulo,
ementa = EXCLUDED.ementa,
resumo_simplificado = EXCLUDED.resumo_simplificado,
updated_at = NOW();

INSERT INTO documentos_politicos (id_documento_origem, titulo, tipo, data_publicacao, url_fonte, ementa, conteudo_original, resumo_simplificado, created_at, updated_at)
VALUES
('votacao-2',
'Lei Geral do Licenciamento Ambiental (PL 2159/2021)',
'votacao',
NULL,
NULL,
'Nova lei que simplifica o processo de licenciamento ambiental: prazos, licença única e digitalização. Debates sobre flexibilização ambiental.',
'Nova lei que simplifica o processo de licenciamento ambiental: prazos, licença única e digitalização. Debates sobre flexibilização ambiental.',
'Lei Geral do Licenciamento Ambiental (resumo)',
NOW(),
NOW()
)
ON CONFLICT (id_documento_origem) DO UPDATE
SET titulo = EXCLUDED.titulo,
ementa = EXCLUDED.ementa,
resumo_simplificado = EXCLUDED.resumo_simplificado,
updated_at = NOW();

INSERT INTO documentos_politicos (id_documento_origem, titulo, tipo, data_publicacao, url_fonte, ementa, conteudo_original, resumo_simplificado, created_at, updated_at)
VALUES
('votacao-3',
'Reforma Tributária (PEC 45/2019)',
'votacao',
NULL,
NULL,
'Reforma que propõe substituir diversos impostos por novos modelos (CBS/IBS). Simplificação e redistribuição do ônus tributário.',
'Reforma que propõe substituir diversos impostos por novos modelos (CBS/IBS).',
'Reforma Tributária (resumo)',
NOW(),
NOW()
)
ON CONFLICT (id_documento_origem) DO UPDATE
SET titulo = EXCLUDED.titulo,
ementa = EXCLUDED.ementa,
resumo_simplificado = EXCLUDED.resumo_simplificado,
updated_at = NOW();

INSERT INTO documentos_politicos (id_documento_origem, titulo, tipo, data_publicacao, url_fonte, ementa, conteudo_original, resumo_simplificado, created_at, updated_at)
VALUES
('votacao-4',
'Novo Arcabouço Fiscal (PLP 93/2023)',
'votacao',
NULL,
NULL,
'Substitui teto de gastos por novas regras fiscais; define limites e gatilhos para controle de despesas.',
'Substitui teto de gastos por novas regras fiscais; define limites e gatilhos para controle de despesas.',
'Novo Arcabouço Fiscal (resumo)',
NOW(),
NOW()
)
ON CONFLICT (id_documento_origem) DO UPDATE
SET titulo = EXCLUDED.titulo,
ementa = EXCLUDED.ementa,
resumo_simplificado = EXCLUDED.resumo_simplificado,
updated_at = NOW();

INSERT INTO documentos_politicos (id_documento_origem, titulo, tipo, data_publicacao, url_fonte, ementa, conteudo_original, resumo_simplificado, created_at, updated_at)
VALUES
('votacao-5',
'Imunidade Parlamentar (PEC 5/2021)',
'votacao',
NULL,
NULL,
'Proposta para ampliar imunidade parlamentar, discutindo limites e impactos para investigações.',
'Proposta para ampliar imunidade parlamentar, discutindo limites e impactos para investigações.',
'Imunidade Parlamentar (resumo)',
NOW(),
NOW()
)
ON CONFLICT (id_documento_origem) DO UPDATE
SET titulo = EXCLUDED.titulo,
ementa = EXCLUDED.ementa,
resumo_simplificado = EXCLUDED.resumo_simplificado,
updated_at = NOW();

INSERT INTO documentos_politicos (id_documento_origem, titulo, tipo, data_publicacao, url_fonte, ementa, conteudo_original, resumo_simplificado, created_at, updated_at)
VALUES
('votacao-6',
'Cotas Raciais em Concursos Públicos (Lei 12.990/2014 - Renovação)',
'votacao',
NULL,
NULL,
'Renovação/expansão da política de cotas raciais para concursos públicos, mantendo percentuais e mecanismos de verificação.',
'Renovação/expansão da política de cotas raciais para concursos públicos.',
'Cotas Raciais em Concursos Públicos (resumo)',
NOW(),
NOW()
)
ON CONFLICT (id_documento_origem) DO UPDATE
SET titulo = EXCLUDED.titulo,
ementa = EXCLUDED.ementa,
resumo_simplificado = EXCLUDED.resumo_simplificado,
updated_at = NOW();

COMMIT;

BEGIN;

CREATE TEMP TABLE tmp_votes (
votacao_num INT,
nome TEXT,
voto TEXT
) ON COMMIT DROP;

INSERT INTO tmp_votes VALUES
-- Nikolas Ferreira: [None, 'SIM', 'NAO', 'NAO', 'SIM', 'NAO']
(2, 'Nikolas Ferreira', 'SIM'),
(3, 'Nikolas Ferreira', 'NAO'),
(4, 'Nikolas Ferreira', 'NAO'),
(5, 'Nikolas Ferreira', 'SIM'),
(6, 'Nikolas Ferreira', 'NAO'),

-- Guilherme Boulos: ['NAO', 'NAO', 'SIM', 'NAO', 'NAO', 'SIM']
(1, 'Guilherme Boulos', 'NAO'),
(2, 'Guilherme Boulos', 'NAO'),
(3, 'Guilherme Boulos', 'SIM'),
(4, 'Guilherme Boulos', 'NAO'),
(5, 'Guilherme Boulos', 'NAO'),
(6, 'Guilherme Boulos', 'SIM'),

-- Ricardo Salles: ['SIM', None, 'NAO', 'NAO', None, 'NAO']
(1, 'Ricardo Salles', 'SIM'),
(3, 'Ricardo Salles', 'NAO'),
(4, 'Ricardo Salles', 'NAO'),
(6, 'Ricardo Salles', 'NAO'),

-- Tabata Amaral: ['NAO', 'NAO', 'SIM', 'SIM', 'NAO', 'SIM']
(1, 'Tabata Amaral', 'NAO'),
(2, 'Tabata Amaral', 'NAO'),
(3, 'Tabata Amaral', 'SIM'),
(4, 'Tabata Amaral', 'SIM'),
(5, 'Tabata Amaral', 'NAO'),
(6, 'Tabata Amaral', 'SIM'),

-- Celso Russomanno: [None, 'SIM', 'SIM', 'SIM', 'SIM', 'SIM']
(2, 'Celso Russomanno', 'SIM'),
(3, 'Celso Russomanno', 'SIM'),
(4, 'Celso Russomanno', 'SIM'),
(5, 'Celso Russomanno', 'SIM'),
(6, 'Celso Russomanno', 'SIM'),

-- Kim Kataguiri: ['SIM', 'SIM', 'SIM', 'NAO', 'NAO', 'NAO']
(1, 'Kim Kataguiri', 'SIM'),
(2, 'Kim Kataguiri', 'SIM'),
(3, 'Kim Kataguiri', 'SIM'),
(4, 'Kim Kataguiri', 'NAO'),
(5, 'Kim Kataguiri', 'NAO'),
(6, 'Kim Kataguiri', 'NAO'),

-- Amom Mandel: ['NAO', 'NAO', 'SIM', 'SIM', 'NAO', 'SIM']
(1, 'Amom Mandel', 'NAO'),
(2, 'Amom Mandel', 'NAO'),
(3, 'Amom Mandel', 'SIM'),
(4, 'Amom Mandel', 'SIM'),
(5, 'Amom Mandel', 'NAO'),
(6, 'Amom Mandel', 'SIM'),

-- Erika Hilton: ['NAO', 'NAO', 'SIM', 'NAO', 'NAO', 'SIM']
(1, 'Erika Hilton', 'NAO'),
(2, 'Erika Hilton', 'NAO'),
(3, 'Erika Hilton', 'SIM'),
(4, 'Erika Hilton', 'NAO'),
(5, 'Erika Hilton', 'NAO'),
(6, 'Erika Hilton', 'SIM'),

-- Delegado Palumbo: ['SIM', 'SIM', 'NAO', 'NAO', 'NAO', 'NAO']
(1, 'Delegado Palumbo', 'SIM'),
(2, 'Delegado Palumbo', 'SIM'),
(3, 'Delegado Palumbo', 'NAO'),
(4, 'Delegado Palumbo', 'NAO'),
(5, 'Delegado Palumbo', 'NAO'),
(6, 'Delegado Palumbo', 'NAO'),

-- Hercílio Coelho Diniz: ['SIM', 'NAO', 'SIM', 'SIM', 'SIM', 'SIM']
(1, 'Hercílio Coelho Diniz', 'SIM'),
(2, 'Hercílio Coelho Diniz', 'NAO'),
(3, 'Hercílio Coelho Diniz', 'SIM'),
(4, 'Hercílio Coelho Diniz', 'SIM'),
(5, 'Hercílio Coelho Diniz', 'SIM'),
(6, 'Hercílio Coelho Diniz', 'SIM')
;

-- mapping CTE para ligar nome -> id_camara
WITH mapping(nome, id_camara, id_uuid) AS (
VALUES
('Nikolas Ferreira', 209787, '470a3d7c-de66-432b-8496-7f192bc1036c'::uuid),
('Guilherme Boulos', 220639, 'a6e54a4d-31f9-4afb-9679-ea2f1e23dd88'::uuid),
('Ricardo Salles', 220633, '09d41dd7-a991-41c8-9750-2998117965dc'::uuid),
('Tabata Amaral', 204534, '8c6a4a08-a3ef-44d2-9c5f-452374438c5f'::uuid),
('Celso Russomanno', 73441, '070bb287-2cb8-4f72-984d-359ea7d670b0'::uuid),
('Kim Kataguiri', 204536, '09beda65-18c8-4120-919f-15f51a4e543b'::uuid),
('Amom Mandel', 220715, '98dd4786-666a-4f13-837e-208d94739ce6'::uuid),
('Erika Hilton', 220645, '816fdbd3-4830-4eae-9cd5-9b5949166037'::uuid),
('Delegado Palumbo', 220652, '80d6c6db-b15b-4ee5-95c0-94c167340da3'::uuid),
('Hercílio Coelho Diniz', 204539, 'b2b636ed-780e-4b56-a072-b6f6e7115fba'::uuid)
)
INSERT INTO votos_documento (documento_id, politico_id, voto, created_at, updated_at)
SELECT
dp.id AS documento_id,
p.id AS politico_id,
tv.voto,
NOW() AS created_at,
NOW() AS updated_at
FROM tmp_votes tv
JOIN mapping m ON lower(trim(m.nome)) = lower(trim(tv.nome))
JOIN politicos p ON p.id_camara = m.id_camara
JOIN documentos_politicos dp ON dp.id_documento_origem = ('votacao-' || tv.votacao_num::text)
WHERE NOT EXISTS (
SELECT 1 FROM votos_documento vd
WHERE vd.documento_id = dp.id AND vd.politico_id = p.id
)
;

COMMIT;