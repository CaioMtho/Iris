# Guia de Contribuição para o Projeto Íris

Bem-vindo(a) ao projeto Íris! Agradecemos o seu interesse em contribuir. Para garantir a qualidade e a consistência do código e da documentação, siga as diretrizes abaixo.

## 1. Commits Semânticos

Utilizamos [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) para padronizar as mensagens de commit. Isso facilita a leitura do histórico do projeto, a geração automática de changelogs e a compreensão das mudanças.

### Formato da Mensagem de Commit:

```
<tipo>[escopo opcional]: <descrição curta>

[corpo opcional]

[rodapé opcional]
```

*   **`<tipo>`**: Obrigatório. Define o tipo de mudança que o commit representa.
*   **`[escopo opcional]`**: Opcional. Indica a parte do projeto que foi afetada pela mudança (ex: `auth`, `parser`, `backend`, `frontend`, `db`).
*   **`<descrição curta>`**: Obrigatório. Uma descrição concisa da mudança, em imperativo e com até 50 caracteres.

### Tipos de Commit:

| Tipo       | Descrição                                                              |
| :--------- | :--------------------------------------------------------------------- |
| `feat`     | Nova funcionalidade (feature).                                         |
| `fix`      | Correção de um bug.                                                    |
| `docs`     | Alterações na documentação (ex: README, guias).                        |
| `style`    | Mudanças de formatação, semântica, linting (não afeta o código).       |
| `refactor` | Reestruturação de código sem mudança de funcionalidade ou correção.    |
| `test`     | Adição ou ajuste de testes (unitários, integração, e2e).               |
| `chore`    | Tarefas auxiliares que não afetam o código da aplicação (build, linter, dependências, etc.). |

### Exemplos de Commits:

```
feat(auth): adicionar endpoint de login via OAuth
fix(parser): corrigir extração de datas no formato DD/MM/AAAA
docs(readme): atualizar instruções de setup
chore(ci): ajustar workflow do GitHub Actions
refactor(search): limpar funções duplicadas
```

## 2. Gerenciamento de Branches

Adotamos um fluxo de trabalho baseado em branches para organizar o desenvolvimento e garantir a estabilidade do projeto.

### Branches Principais:

*   **`main`**: Esta branch deve estar **sempre estável** e pronta para deploy. Todas as novas funcionalidades e correções de bugs devem ser desenvolvidas em branches separadas e, após revisão, mescladas para `main`.

### Branches de Desenvolvimento:

Para cada nova funcionalidade ou correção de bug, crie uma branch a partir de `main` com o seguinte padrão:

*   **`feature/<descrição-curta-da-feature>`** (para novas funcionalidades)
*   **`fix/<descrição-curta-do-bug>`** (para correção de bugs)

**Exemplos:**

*   `git checkout -b feature/analise-ideologica-usuario`
*   `git checkout -b fix/bug-calculo-ici`

## 3. Pull Requests (PRs) e Code Review

Todas as mudanças devem ser submetidas através de Pull Requests (PRs) para revisão de código.

### Processo de PR:

1.  **Abra um PR:** Após concluir suas alterações em sua branch de desenvolvimento, abra um Pull Request para a branch `main`.
2.  **Descrição do PR:** Forneça uma descrição clara e concisa das mudanças, referenciando quaisquer issues relacionadas.
3.  **Code Review:** Seu código será revisado por outro(s) membro(s) da equipe. Esteja aberto(a) a feedback e sugestões de melhoria.
4.  **Aprovação e Merge:** Após a aprovação do code review, o PR será mesclado diretamente na branch `main`.

## 4. Versionamento e Releases

Utilizamos [Versionamento Semântico](https://semver.org/lang/pt-BR/) para gerenciar as versões do projeto. Isso significa que cada release terá um número de versão no formato `MAJOR.MINOR.PATCH`.

*   **`MAJOR`**: Incrementado para mudanças incompatíveis de API.
*   **`MINOR`**: Incrementado para novas funcionalidades que são compatíveis com versões anteriores.
*   **`PATCH`**: Incrementado para correções de bugs compatíveis com versões anteriores.

### Tags Semânticas:

Marque tags semânticas para cada release no formato `vX.Y.Z` (ex: `v1.0.0`, `v1.1.0`, `v1.0.1`).

**Exemplo:**

```bash
git tag -a v1.0.0 -m "Primeira versão estável do protótipo"
git push origin v1.0.0
```
