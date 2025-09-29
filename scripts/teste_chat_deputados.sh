#!/bin/bash

# Lista de nomes dos deputados
deputados=(
  "Nikolas Ferreira"
  "Guilherme Boulos"
  "Ricardo Salles"
  "Tabata Amaral"
  "Celso Russomanno"
  "Kim Kataguiri"
  "Amom Mandel"
  "Erika Hilton"
  "Delegado Palumbo"
  "Hercílio Coelho Diniz"
)

# Loop para enviar uma requisição para cada deputado
for nome in "${deputados[@]}"; do
  echo "Enviando requisição para: $nome"
  curl -X 'POST' \
    'http://localhost:8000/api/v1/chat/' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d "{
      \"message\": \"Quem é $nome?\",
      \"session_id\": \"string\",
      \"user_id\": \"string\",
      \"max_tokens\": 512,
      \"temperature\": 0
    }"
  echo -e "\n---\n"
done

