#!/usr/bin/env python3
import json
import re
import subprocess
from pathlib import Path

def baixar_dados_teste():
    caminho_script = Path(__file__).resolve().parent / "baixar_dados_abertos.sh"
    if not caminho_script.exists():
        raise FileNotFoundError(f"Script {caminho_script} não encontrado.")
    
    try:
        subprocess.run(["bash", str(caminho_script)], check=True)
        print("Download concluído")
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o script de download: {e}")
        raise

PADRAO_CARACTERES_ESPECIAIS = re.compile(r"[^a-zA-Z0-9\sáéíóúâêôãõçàèìòùü]")
MULTIPLOS_ESPACOS = re.compile(r'\s+')

def limpar_texto(texto: str) -> str:
    if not isinstance(texto, str):
        return texto
    
    texto = texto.lower()
    texto = PADRAO_CARACTERES_ESPECIAIS.sub(' ', texto)
    texto = MULTIPLOS_ESPACOS.sub(' ', texto).strip()
    return texto

# Campos a serem removidos de cada tipo de arquivo
CAMPOS_REMOVER = {
    "orgaos.json": {"idOrgao", "uriOrgao", "nomePublicacao", "codTitulo", "dataInicio", "dataFim"},
    "frentes.json": {"id", "uri", "idLegislatura"},
    "proposicoes.json": {"id", "uri", "codTipo"},
}

def processar_dados_json(caminho: Path, tipo: str) -> dict:
    try:
        with open(caminho, 'r', encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
        
        remover = CAMPOS_REMOVER.get(tipo, set())
        
        if "dados" in dados and isinstance(dados["dados"], list):
            processados = []
            for item in dados["dados"]:
                item = {k: v for k, v in item.items() if k not in remover}
                
                for key in item:
                    if isinstance(item[key], str):
                        item[key] = limpar_texto(item[key])
                
                processados.append(item)
            
            dados["dados"] = processados
        
        return dados
    
    except Exception as e:
        print(f"Erro ao processar {caminho}: {e}")
        return {}

def processar_dados_completos(dir_base: Path):
    if not dir_base.exists():
        print(f"Diretório {dir_base} não existe!")
        return
    
    for dir_deputado in dir_base.iterdir():
        if dir_deputado.is_dir():
            print(f"Processando deputado: {dir_deputado.name}")
            
            for arquivo_json in dir_deputado.glob("*.json"):
                print(f"  Processando: {arquivo_json.name}")
                
                dados_processados = processar_dados_json(arquivo_json, arquivo_json.name)
                
                if dados_processados:
                    try:
                        with open(arquivo_json, 'w', encoding='utf-8') as arquivo:
                            json.dump(dados_processados, arquivo, ensure_ascii=False, indent=2)
                    except Exception as e:
                        print(f"Erro ao salvar {arquivo_json}: {e}")

def main():
    print("Iniciando processamento de dados abertos...")
    
    try:
        baixar_dados_teste()
    except Exception as e:
        print(f"Erro no download: {e}")
        return
    
    dir_base = Path(__file__).resolve().parent.parent / "dados_teste"
    processar_dados_completos(dir_base)
    
    print("Processamento concluído.")

if __name__ == "__main__":
    main()