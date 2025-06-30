import re

PADRAO_CARACTERES_ESPECIAIS = re.compile(r"[^a-zA-Z0-9\sáéíóúâêôãõçàèìòùü]")
MULTIPLOS_ESPACOS = re.compile(r'\s+')

def limpar_texto(texto: str) -> str:
    
    texto = texto.lower()
    texto = PADRAO_CARACTERES_ESPECIAIS.sub(' ', texto)
    texto = MULTIPLOS_ESPACOS.sub(' ', texto).strip()
    
    return texto