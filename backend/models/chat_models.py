import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from backend.db.database import Base

class SessionMessage(Base):
    __tablename__ = "session_messages"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    session_id = sa.Column(sa.Text, nullable=False, index=True)
    role = sa.Column(sa.Text, nullable=False)  # 'user' | 'assistant' | 'system'
    message = sa.Column(sa.Text, nullable=False)
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))

class ResponseLog(Base):
    __tablename__ = "response_log"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    session_id = sa.Column(sa.Text, nullable=True, index=True)
    user_id = sa.Column(sa.Text, nullable=True)
    prompt = sa.Column(sa.Text, nullable=True)
    response = sa.Column(sa.Text, nullable=True)
    sources = sa.Column(JSONB, nullable=True)
    created_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
