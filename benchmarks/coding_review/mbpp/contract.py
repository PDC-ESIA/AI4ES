"""Tradução de um problema MBPP para os artefatos que o Coder consome.

Dois artefatos são produzidos por problema (mesmo padrão do HumanEval):

1. **Contrato de task** (`TASK-XXX.json`): gravado em `coder/tasks/` para que o
   coder possa lê-lo via `tool_ler_workspace`. Também é o formato que o harness
   nativo espera (campos `id`, `description`, `acceptance_criteria`, `contract`).
2. **Mensagem de entrada** (o "contrato" que normalmente vem do context_engineer):
   define stack (Python), tipo de produto (library) e as regras operacionais do
   benchmark — em especial, o requisito de expor a função-alvo em `solution.py`.

Diferença em relação ao HumanEval: o enunciado do MBPP é só linguagem natural
(sem assinatura de função). Seguindo o protocolo original do benchmark
(Austin et al., 2021), expomos ao coder o PRIMEIRO caso de `test_list` como
exemplo de uso — isso fixa o nome/assinatura da função sem revelar a suíte
completa. A avaliação (ver `grading.py`) roda contra TODOS os itens de
`test_list`, incluindo esse primeiro caso.

Regra de ouro do benchmark (igual ao HumanEval): a função-alvo (`entry_point`)
DEVE existir no nível de módulo de `solution.py`, para que os `assert`s
oficiais possam importá-la de forma determinística.
"""

from __future__ import annotations

from .dataset import MbppProblem

# Nome do arquivo-solução que o coder deve produzir (contrato do benchmark).
SOLUTION_FILENAME = "solution.py"


def task_id_for(problem: MbppProblem) -> str:
    """Identificador de task no formato aceito pelo coder/harness (``TASK-XXX``)."""
    return problem.slug


def build_task_contract(problem: MbppProblem) -> dict:
    """Monta o contrato de task (JSON) gravado em `coder/tasks/`.

    Os `acceptance_criteria` são intencionalmente de alto nível: quem julga a
    correção são os `assert`s oficiais do MBPP, não o harness.
    """
    exemplo = problem.test_list[0] if problem.test_list else ""
    return {
        "id": task_id_for(problem),
        "description": (
            f"Implementar a função `{problem.entry_point}` a partir da "
            f"descrição:\n\n{problem.prompt.strip()}\n\n"
            f"Exemplo de uso (fixa nome e assinatura):\n"
            f"```python\n{exemplo}\n```"
        ),
        "acceptance_criteria": [
            f"A função `{problem.entry_point}` está implementada e disponível no "
            f"nível de módulo do arquivo `{SOLUTION_FILENAME}`.",
            "O comportamento respeita integralmente a descrição e o exemplo fornecidos.",
        ],
        "contract": {
            "tech_stack": "python",
            "product_type": "library",
            "entry_point": problem.entry_point,
            "solution_file": SOLUTION_FILENAME,
        },
    }


def build_coder_message(problem: MbppProblem) -> str:
    """Monta a mensagem de entrada do coder (o "contrato" da sessão).

    Emula a saída do context_engineer: fixa a stack/produto e injeta as regras
    específicas do benchmark que garantem um artefato avaliável.
    """
    exemplo = problem.test_list[0] if problem.test_list else ""
    imports_hint = ""
    if problem.test_imports:
        imports_lista = "\n".join(f"- `{imp}`" for imp in problem.test_imports)
        imports_hint = (
            "\n## Módulos relevantes\n"
            "Os testes desta tarefa usam os seguintes módulos da biblioteca "
            f"padrão (indício do domínio do problema):\n{imports_lista}\n"
        )

    return f"""# CONTRATO DE EXECUÇÃO (benchmark MBPP)

## Stack e produto
- `tech_stack`: Python 3 (somente biblioteca padrão; NÃO adicione dependências).
- `product_type`: library.
- `global_rules`: código limpo, tipado quando possível, sem I/O de rede.

## Tarefa
{problem.prompt.strip()}

Implemente uma função chamada `{problem.entry_point}` que satisfaça a
descrição acima. Este exemplo de uso FIXA o nome e a assinatura esperados
(mas não é a suíte de testes completa — a avaliação usa casos adicionais):

```python
{exemplo}
```
{imports_hint}
## Regras OBRIGATÓRIAS do benchmark (sobrepõem-se a qualquer default)
1. Toda a solução DEVE ficar em um ÚNICO arquivo chamado `{SOLUTION_FILENAME}`.
2. A função `{problem.entry_point}` DEVE ser definida no NÍVEL DE MÓDULO
   (top-level) de `{SOLUTION_FILENAME}`, com a MESMA assinatura do exemplo.
3. Funções auxiliares e imports (apenas biblioteca padrão) podem existir no mesmo
   arquivo, desde que `{problem.entry_point}` continue importável via
   `from solution import {problem.entry_point}`.
4. NÃO escreva a suíte de testes do enunciado: a avaliação usa testes próprios.
   Você ainda deve entregar `run.json` e `README.md` conforme suas regras
   padrão (use `surface: none`), mas eles não afetam a avaliação do benchmark.

Entregue o código agora, persistindo os arquivos via `tool_criar_arquivo`.
"""
