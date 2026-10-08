"""Tradução de uma tarefa BigCodeBench para os artefatos que o Coder consome.

Mesma ideia do `humaneval/contract.py`, com duas diferenças essenciais:

- o contrato PERMITE (e espera) bibliotecas de terceiros — são o objeto do
  benchmark; as bibliotecas sugeridas pela tarefa (`libs`) são listadas;
- o `solution.py` deve conter o código COMPLETO (imports + `task_func`), pois o
  grading executa o arquivo inteiro seguido dos testes oficiais.

Esta issue MEDE o `cr_coder`; o prompt do agente não é alterado — só a mensagem
de entrada do benchmark (que emula a saída do context_engineer).
"""

from __future__ import annotations

from .dataset import BigCodeBenchProblem

# Nome do arquivo-solução que o coder deve produzir (contrato do benchmark).
SOLUTION_FILENAME = "solution.py"


def task_id_for(problem: BigCodeBenchProblem) -> str:
    """Identificador de task no formato aceito pelo coder/harness."""
    return problem.slug


def _libs_texto(problem: BigCodeBenchProblem) -> str:
    return ", ".join(f"`{lib}`" for lib in problem.libs) or "(apenas biblioteca padrão)"


def build_task_contract(problem: BigCodeBenchProblem) -> dict:
    """Monta o contrato de task (JSON) gravado em `coder/tasks/`."""
    return {
        "id": task_id_for(problem),
        "description": (
            f"Implementar a função `{problem.entry_point}` conforme a "
            f"assinatura e docstring fornecidas.\n\n"
            f"```python\n{problem.prompt.strip()}\n```"
        ),
        "acceptance_criteria": [
            f"A função `{problem.entry_point}` está implementada no nível de "
            f"módulo do arquivo `{SOLUTION_FILENAME}`.",
            "O comportamento respeita integralmente a docstring da função.",
        ],
        "contract": {
            "tech_stack": "python",
            "product_type": "library",
            "entry_point": problem.entry_point,
            "solution_file": SOLUTION_FILENAME,
            "libraries": list(problem.libs),
        },
    }


def build_coder_message(problem: BigCodeBenchProblem) -> str:
    """Monta a mensagem de entrada do coder (o "contrato" da sessão)."""
    return f"""# CONTRATO DE EXECUÇÃO (benchmark BigCodeBench — split complete)

## Stack e produto
- `tech_stack`: Python 3.10.
- `product_type`: library.
- Bibliotecas de terceiros SÃO esperadas nesta tarefa e já estão instaladas no
  ambiente de avaliação. Bibliotecas sugeridas: {_libs_texto(problem)}.
- `global_rules`: código limpo, sem I/O de rede e sem efeitos colaterais além
  dos descritos na docstring.

## Tarefa
Implemente a função abaixo COMPLETAMENTE, respeitando exatamente a assinatura, os
imports e a docstring (contrato de comportamento, incluindo as exceções
documentadas):

```python
{problem.prompt.strip()}
```

## Regras OBRIGATÓRIAS do benchmark (sobrepõem-se a qualquer default)
1. Toda a solução DEVE ficar em um ÚNICO arquivo chamado `{SOLUTION_FILENAME}`,
   contendo o código completo: os imports do enunciado + a função.
2. A função `{problem.entry_point}` DEVE ser definida no NÍVEL DE MÓDULO
   (top-level) de `{SOLUTION_FILENAME}`, com a MESMA assinatura do enunciado.
3. Funções auxiliares e imports adicionais podem existir no mesmo arquivo.
4. NÃO escreva a suíte de testes: a avaliação usa testes oficiais próprios.
   Você ainda deve entregar `run.json` e `README.md` conforme suas regras padrão
   (use `surface: none`), mas eles não afetam a avaliação do benchmark.

Entregue o código agora, persistindo os arquivos via `tool_criar_arquivo`.
"""
