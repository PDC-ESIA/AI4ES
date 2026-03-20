# Contribuindo com o Projeto (Gitflow)

Este projeto utiliza o fluxo de trabalho **Gitflow** para gerenciar o versionamento de código. Suas contribuições devem seguir este padrão.

## Branches Principais

- **`main`** (ou `master`): Reflete o estado exato da produção. Restrita a merges vindos de `release` ou `hotfix`.
- **`develop`**: Branch principal de desenvolvimento. O código atual da próxima versão fica centralizado aqui.

## Como Contribuir

### 1. Novas Funcionalidades (`feature/`)
Crie sempre a partir da `develop`. **Obrigatório incluir o número da issue no nome**:
```bash
git checkout develop
git checkout -b feature/123-nome-da-sua-feature
```
*Ao finalizar, abra um Merge Request (MR) / Pull Request (PR) para a `develop`.*

### 2. Correções Emergenciais (`hotfix/`)
Para bugs críticos em produção, crie a partir da `main`. **Inclua o número da issue do bug**:
```bash
git checkout main
git checkout -b hotfix/124-nome-do-bug
```
*Após corrigir, faça o merge tanto na `main` (gerando nova tag) quanto na `develop`.*

### 3. Lançamentos (`release/`)
Para compilar uma nova versão, crie a partir da `develop`:
```bash
git checkout develop
git checkout -b release/vX.Y.Z
```
*Faça os últimos ajustes e, ao concluir, submeta o merge para a `main` (com tag) e para a `develop`.*

## Regras Gerais
- **Nomenclatura de Branches**: Siga o padrão `tipo/numero-da-issue-breve-descricao` (ex: `feature/42-adicionar-login`).
- **Branches Protegidas**: As branches `main` e `develop` são protegidas. O código deve ser integrado a elas **exclusivamente via Merge Request (MR) / Pull Request (PR)**. Nunca realize commits diretos.
- **Commits Descritivos**: A mensagem do commit deve ser curta, objetiva e sempre **conter a referência ao número da issue** de trabalho (ex: `#42 Adiciona validação de login`).
- **Sincronização**: Antes de finalizar sua tarefa, sincronize sua branch com as mudanças mais recentes da branch de destino (ex: `git pull origin develop`).
