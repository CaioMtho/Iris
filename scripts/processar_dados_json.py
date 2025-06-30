import re
import json
from pathlib import Path
from backend.ml.processing import limpar_dados

PADRAO_CARACTERES_ESPECIAIS = re.compile(r"[^a-zA-Z0-9\sáéíóúâêôãõçàèìòùü]")
MULTIPLOS_ESPACOS = re.compile(r'\s+')

# Remoção de campos desnecessários
CAMPOS_REMOVER = {
    "orgaos.json": {"idOrgao", "uriOrgao", "nomePublicacao", "codTitulo", "dataInicio", "dataFim"},
    "frentes.json": {"id", "uri", "idLegislatura"},
    "proposicoes.json": {"id", "uri", "codTipo"},
}

def limpar_texto(texto: str) -> str:
    texto = texto.lower()
    texto = PADRAO_CARACTERES_ESPECIAIS.sub(' ', texto)
    texto = MULTIPLOS_ESPACOS.sub(' ', texto).strip()
    return texto

def processar_dados_json(caminho: Path, tipo: str) -> dict:
    with open(caminho, 'r', encoding='utf-8') as arquivo:
        dados = json.load(arquivo)

    remover = CAMPOS_REMOVER.get(tipo, set())

    if "dados" in dados and isinstance(dados["dados"], list):
        processados = []
        for item in dados["dados"]:
            item = {k: v for k, v in item.items() if k not in remover}

            for key in item:
                if isinstance(item[key], str):
                    item[key] = limpar_dados.limpar_texto(item[key])
            processados.append(item)

        dados["dados"] = processados

    return dados

def processar_dados_completos(dir_base: Path):
    for caminho in dir_base.iterdir():
        if caminho.is_dir():
            for nome_arquivo in ["proposicoes.json", "orgaos.json", "frentes.json"]:
                caminho_json = caminho / nome_arquivo
                if caminho_json.exists():
                    dados_processados = processar_dados_json(caminho_json, nome_arquivo)
                    with open(caminho_json, 'w', encoding='utf-8') as arquivo:
                        json.dump(dados_processados, arquivo, ensure_ascii=False, indent=2)
                    print(f"Processado: {caminho_json}")

if __name__ == "__main__":
    dir_base = Path(__file__).resolve().parent.parent / "dados_teste"
    processar_dados_completos(dir_base)
    print("Processamento concluído.")
