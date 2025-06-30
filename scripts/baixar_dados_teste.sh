#!/bin/bash


BASE_DIR="$(dirname "$(dirname "$(realpath "$0")")")/dados_teste"

#Deputados para teste
declare -A deputados=(
  ["nikolas_ferreira"]="209787"
  ["guilherme_boulos"]="220639"
  ["ricardo_salles"]="220633"
  ["tabata_amaral"]="204534"
  ["celso_russomanno"]="73441"
  ["kim_katagiri"]="204536"
  ["amom_mandel"]="220715"
  ["erika_hilton"]="220645"
  ["delegado_palumbo"]="220652"
  ["hercilio_coelho_diniz"]="204539"
)

#Loop para cada deputado
for nome in "${!deputados[@]}"; do
  codigo="${deputados[$nome]}"
  DIR_DEPUTADO="$BASE_DIR/${nome}"

  #Criar pasta do deputado
  mkdir -p "$DIR_DEPUTADO"

  echo "Baixando dados para ${nome} (código: ${codigo})..."
  
  #Proposições
  curl -s -X GET \
    "https://dadosabertos.camara.leg.br/api/v2/proposicoes?idDeputadoAutor=${codigo}&ordem=ASC&ordenarPor=id&itens=100" \
    -H "accept: application/json" \
    -o "${DIR_DEPUTADO}/proposicoes.json"

  #Frentes
  curl -s -X GET \
    "https://dadosabertos.camara.leg.br/api/v2/deputados/${codigo}/frentes" \
    -H "accept: application/json" \
    -o "${DIR_DEPUTADO}/frentes.json"

  #Órgãos
  curl -s -X GET \
    "https://dadosabertos.camara.leg.br/api/v2/deputados/${codigo}/orgaos?itens=100&ordem=ASC&ordenarPor=dataInicio" \
    -H "accept: application/json" \
    -o "${DIR_DEPUTADO}/orgaos.json"

  echo "Todos os arquivos para ${nome} foram salvos em ${DIR_DEPUTADO}/."
done

echo "Download concluído" 

