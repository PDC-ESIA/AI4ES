# Agente Revisor (Reviewer)

## 1. Visão Geral
- **Identificação:** Role de Code Review.
- **Propósito:** Inspecionar diferenças de código (Diff) geradas pelo Coder, garantindo a qualidade e segurança no ciclo ES.
- **Tecnologias:** Google ADK, Git Diff, LiteLLM.

## 2. Funcionalidades
Leitura técnica de diffs não mergeados e geração estruturada de relatórios de revisão de código, validando boas práticas e identificando vulnerabilidades.

## 3. Como executar ou testar
- **Pré-requisitos:** `.env` configurado e commits recentes locais no repositório.
- **Instalação:** `uv sync`.
- **Execução:** Como root isolado ou como etapa subsequente do Coder no workflow.
- **Suíte de Testes:** *Não implementada.* Nenhuma suíte em `adk/tests/` cobre este agente ainda.

## 4. Entradas e Saídas
- **Entrada:** Modificações de código (Git diff) do agente de codificação.
- **Saída:** Relatório em texto aprovando as alterações ou solicitando correções (`output_key="review"`).

## 5. Cenário de Teste Específico
Fornecer um diff contendo credenciais (senhas ou tokens) hardcoded no código. O agente deve identificar a falha de segurança e reprovar a revisão no relatório. *(Status: Cenário E2E Não Implementado)*

## 6. Lista de Erros Identificados
- *Diff Vazio:* Ocorre se o Coder falhou em gerar commits. A tool de ler diff retornará vazio, travando a validação. Solução: Validação do output do coder antes do Reviewer agir.
