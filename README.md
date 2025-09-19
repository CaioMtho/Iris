# Iris

Bem-vindo(a) ao repositório da Iris!

Uma plataforma de analise política e ideológica automatizada para classificar, avaliar e comparar a atuação de representantes públicos e a população, de forma a aproximar os eleitores dos eleitos e promover o letramento político.

O protótipo deste projeto estará em exposição na [FETEPS](https://feteps.cps.sp.gov.br/), selecionamos votações e deputados pertinentes e submetemos usuários às mesmas votações, calculando afinidade.

## Como usar

O protótipo funcional para exposição está disponível, clone ou baixe o projeto:

```bash
git clone https://github.com/CaioMtho/Iris.git
```

Crie um arquivo .env na raiz do projeto com uma entrada:

```bash
DB_PASSWORD=INSIRAUMASENHA
```

Rode com docker-compose:

```bash
## na pasta raiz do projeto
docker-compose up --build
```

Ou abra usando o Dev Container (extensão do vscode ou Github Codespaces).
O servidor por padrão estará rodando em http://localhost:8000, acesse o endpoint /docs para acessar a documentação interativa.

## Documentação

Para detalhes do projeto, consulte a **[wiki](https://github.com/CaioMtho/Iris/wiki)**.

## Principais tecnologias

*   **Backend:** Python 3.11, FastAPI
*   **Frontend:** HTML, CSS, JS 
*   **Banco de Dados:** PostgreSQL
*   **Containerização:** Docker e Docker Compose

[Hudson Henrique](https://github.com/HudsonDomin) & [Caio Matheus](https://github.com/CaioMtho) 

