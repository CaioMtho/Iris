"""Conecção com o banco de dados"""
from os import getenv, environ
from dotenv import load_dotenv
from psycopg2 import connect

def conectar():
    """Verifica o arquivo .env primeiro e então a variável de ambiente padrão"""
    load_dotenv()
    if "USUARIO_DATABASE_URL" in environ:
        return connect(getenv("USUARIO_DATABASE_URL"))
    return connect(getenv("DATABASE_URL"))
