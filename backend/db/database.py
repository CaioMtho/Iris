"""Conexão com o banco de dados"""
from os import getenv
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

def get_database_url() -> str:
    """Tenta obter USUARIO_DATABASE_URL, depois DATABASE_URL. Lança exceção se ambos forem None."""
    load_dotenv()

    usuario_url = getenv("USUARIO_DATABASE_URL")
    if usuario_url:
        return usuario_url

    default_url = getenv("DATABASE_URL")
    if default_url:
        return default_url

    raise RuntimeError("Nenhuma URL de banco de dados encontrada nas variáveis de ambiente.")


engine = create_engine(get_database_url(), echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
