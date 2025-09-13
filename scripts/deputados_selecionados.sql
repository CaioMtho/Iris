
INSERT INTO politicos (id_camara, nome, partido, uf, cargo)
VALUES
(220715, 'Nikolas Ferreira', 'PL', 'MG', 'Deputado Federal'),
(220639, 'Guilherme Boulos', 'PSOL', 'SP', 'Deputado Federal'),
(220633, 'Ricardo Salles', 'NOVO', 'SP', 'Deputado Federal'),
(204534, 'Tabata Amaral', 'PSB', 'SP', 'Deputado Federal'),
(73441, 'Celso Russomanno', 'Republicanos', 'SP', 'Deputado Federal'),
(204536, 'Kim Kataguiri', 'UNIÃO', 'SP', 'Deputado Federal'),
(220715, 'Amom Mandel', 'Cidadania', 'PE', 'Deputado Federal'),
(220645, 'Erika Hilton', 'PSOL', 'SP', 'Deputado Federal'),
(220652, 'Delegado Palumbo', 'MDB', 'SP', 'Deputado Federal'),
(204539, 'Hercílio Coelho Diniz', 'MDB', 'MG', 'Deputado Federal')
ON CONFLICT (id_camara) DO NOTHING;
