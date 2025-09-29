import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP, BIGINT
from pgvector.sqlalchemy import Vector
from backend.db.database import Base

class Politico(Base):
    __tablename__ = "politicos"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    id_camara = sa.Column(BIGINT, unique=True, index=True, nullable=True)
    nome = sa.Column(sa.String(255), nullable=False)
    partido = sa.Column(sa.String(50))
    uf = sa.Column(sa.String(2))
    cargo = sa.Column(sa.String(100))
    votos_2022 = sa.Column(sa.Integer)
    ativo = sa.Column(sa.Boolean, default=True)
    ideologia_eco = sa.Column(sa.Float)
    ideologia_soc = sa.Column(sa.Float)
    ideologia_aut = sa.Column(sa.Float)
    ideologia_amb = sa.Column(sa.Float)
    ideologia_est = sa.Column(sa.Float)
    embedding_ideologia = sa.Column(Vector(768))
    embedding_biografia = sa.Column(Vector(768))
    ici = sa.Column(sa.Float)
    historico_ici = sa.Column(JSONB, default="{}")
    biografia_resumo = sa.Column(sa.Text)
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))

class DocumentoPolitico(Base):
    __tablename__ = "documentos_politicos"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    id_documento_origem = sa.Column(sa.Text, unique=True, nullable=True)
    politico_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("politicos.id"), nullable=True)
    titulo = sa.Column(sa.String(500), nullable=False)
    tipo = sa.Column(sa.String(50), nullable=False)
    data_publicacao = sa.Column(sa.Date)
    url_fonte = sa.Column(sa.Text)
    ementa = sa.Column(sa.Text)
    conteudo_original = sa.Column(sa.Text)
    resumo_simplificado = sa.Column(sa.Text)
    embedding_documento = sa.Column(Vector(768))
    embedding_titulo = sa.Column(Vector(768))
    embedding_ementa = sa.Column(Vector(768))
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))

class Votacao(Base):
    __tablename__ = "votacoes"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    id_votacao_origem = sa.Column(sa.Text, unique=True, nullable=True)
    documento_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("documentos_politicos.id"), nullable=True)
    data_votacao = sa.Column(sa.Date)
    resultado = sa.Column(sa.String(50), sa.CheckConstraint("resultado IN ('aprovado','rejeitado','em_tramitacao','arquivado')"))
    descricao = sa.Column(sa.Text)
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))

class VotoPolitico(Base):
    __tablename__ = "votos_politicos"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    votacao_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("votacoes.id", ondelete="CASCADE"))
    politico_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("politicos.id", ondelete="CASCADE"))
    voto = sa.Column(sa.String(20), sa.CheckConstraint("voto IN ('sim','nao','abstencao','ausente')"))
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))

class VotoDocumento(Base):
    __tablename__ = "votos_documento"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    documento_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("documentos_politicos.id", ondelete="CASCADE"), nullable=False)
    politico_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("politicos.id", ondelete="CASCADE"), nullable=False)
    voto = sa.Column(sa.Text, nullable=False)
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    
    __table_args__ = (
        sa.UniqueConstraint('documento_id', 'politico_id', name='votos_documento_unq'),
    )

class VotacaoEixo(Base):
    __tablename__ = "votacoes_eixo"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    votacao_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("votacoes.id", ondelete="CASCADE"))
    eixo = sa.Column(sa.Text, nullable=False)  # 'eco','soc','aut','amb','est'
    eixo_conf = sa.Column(sa.Float)  # confiança [0..1]
    metodo = sa.Column(sa.Text)  # 'keyword','embedding','manual'
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))

class EixoAnchor(Base):
    __tablename__ = "eixo_anchors"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    eixo = sa.Column(sa.Text, nullable=False)  # 'eco','soc','aut','amb','est'
    polaridade = sa.Column(sa.String(10), sa.CheckConstraint("polaridade IN ('pos','neg')"), nullable=False)
    texto = sa.Column(sa.Text, nullable=False)  # frase/ementa usada como âncora
    fonte = sa.Column(sa.Text)
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))

class UsuarioPerfilIdeologico(Base):
    __tablename__ = "usuarios_perfis_ideologicos"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    data_criacao = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    ideologia_eco = sa.Column(sa.Float)
    ideologia_soc = sa.Column(sa.Float)
    ideologia_aut = sa.Column(sa.Float)
    ideologia_amb = sa.Column(sa.Float)
    ideologia_est = sa.Column(sa.Float)
    embedding_ideologia = sa.Column(Vector(768))
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))

class QueryEmbeddingCache(Base):
    __tablename__ = "query_embeddings_cache"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    query_text = sa.Column(sa.Text, nullable=False)
    query_hash = sa.Column(sa.String(64), unique=True, nullable=False)
    embedding = sa.Column(Vector(768), nullable=False)
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))