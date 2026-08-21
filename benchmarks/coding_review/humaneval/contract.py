"""Tradução de um problema HumanEval para os artefatos que o Coder consome.

Dois artefatos são produzidos por problema:

1. **Contrato de task** (`TASK-XXX.json`): gravado em `coder/tasks/` para que o
   coder possa lê-lo via `tool_ler_workspace`. Também é o formato que o harness
   nativo espera (campos `id`, `description`, `acceptance_criteria`, `contract`).
2. **Mensagem de entrada** (o "contrato" que normalmente vem do context_engineer):
   define stack (Python), tipo de produto (library) e as regras operacionais do
   benchmark — em especial, o requisito de expor a função-alvo em `solution.py`.

Regra de ouro do benchmark: a função-alvo (`entry_point`) DEVE existir no nível
de módulo de `solution.py`, para que o teste canônico possa importá-la de forma
determinística.
"""

from __future__ import annotations

from .dataset import HumanEvalProblem

# Nome do arquivo-solução que o coder deve produzir (contrato do benchmark).
SOLUTION_FILENAME = "solution.py"


def task_id_for(problem: HumanEvalProblem) -> str:
    """Identificador de task no formato aceito pelo coder/harness (``TASK-XXX``)."""
    return problem.slug


def build_task_contract(problem: HumanEvalProblem) -> dict:
    """Monta o contrato de task (JSON) gravado em `coder/tasks/`.

    Os `acceptance_criteria` são intencionalmente de alto nível: quem julga a
    correção é o teste canônico do HumanEval, não o harness.
    """
    return {
        "id": task_id_for(problem),
        "description": (
            f"Implementar a função `{problem.entry_point}` conforme a "
            f"assinatura e docstring fornecidas.\n\n"
            f"```python\n{problem.prompt.strip()}\n```"
        ),
        "acceptance_criteria": [
            f"A função `{problem.entry_point}` está implementada e disponível no "
            f"nível de módulo do arquivo `{SOLUTION_FILENAME}`.",
            "O comportamento respeita integralmente a docstring da função.",
        ],
        "contract": {
            "tech_stack": "python",
            "product_type": "library",
            "entry_point": problem.entry_point,
            "solution_file": SOLUTION_FILENAME,
        },
    }


def build_coder_message(problem: HumanEvalProblem) -> str:
    """Monta a mensagem de entrada do coder (o "contrato" da sessão).

    Emula a saída do context_engineer: fixa a stack/produto e injeta as regras
    específicas do benchmark que garantem um artefato avaliável.
    """
    return f"""# CONTRATO DE EXECUÇÃO (benchmark HumanEval)

## Stack e produto
- `tech_stack`: Python 3 (somente biblioteca padrão; NÃO adicione dependências).
- `product_type`: library.
- `global_rules`: código limpo, tipado quando possível, sem I/O de rede.

## Tarefa
Implemente a função abaixo COMPLETAMENTE, respeitando exatamente a assinatura e
a docstring (contrato de comportamento):

```python
{problem.prompt.strip()}
```

## Regras OBRIGATÓRIAS do benchmark (sobrepõem-se a qualquer default)
1. Toda a solução DEVE ficar em um ÚNICO arquivo chamado `{SOLUTION_FILENAME}`.
2. A função `{problem.entry_point}` DEVE ser definida no NÍVEL DE MÓDULO
   (top-level) de `{SOLUTION_FILENAME}`, com a MESMA assinatura do enunciado.
3. Funções auxiliares e imports (apenas biblioteca padrão) podem existir no mesmo
   arquivo, desde que `{problem.entry_point}` continue importável via
   `from solution import {problem.entry_point}`.
4. NÃO escreva a suíte de testes do enunciado: a avaliação usa testes próprios.
   Você ainda deve entregar `run.json` e `README.md` conforme suas regras padrão
   (use `surface: none`), mas eles não afetam a avaliação do benchmark.

Entregue o código agora, persistindo os arquivos via `tool_criar_arquivo`.
"""
