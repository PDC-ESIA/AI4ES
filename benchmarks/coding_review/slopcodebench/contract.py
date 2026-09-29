"""Tradução de um checkpoint do SlopCodeBench para os artefatos que o Coder consome.

Dois artefatos são produzidos por checkpoint, como no benchmark HumanEval:

1. **Contrato de task** (``TASK-XXX.json``): gravado em ``coder/tasks/`` para que
   o coder possa lê-lo via ``tool_ler_workspace``.
2. **Mensagem de entrada** (o "contrato" que normalmente vem do
   context_engineer): fixa stack e tipo de produto e carrega o prompt do
   checkpoint.

O prompt do checkpoint em si NÃO é montado aqui: é o template oficial
``just-solve`` do SlopCodeBench (Listing 8 do paper), renderizado pelo próprio
harness (``grading.render_prompt``) e repassado sem alteração.
"""

from __future__ import annotations

from .dataset import ScbProblem


def task_id_for(problem: ScbProblem, checkpoint: str) -> str:
    """Identificador de task no formato aceito pelo coder (``TASK-XXX``)."""
    numero = checkpoint.rsplit("_", 1)[-1]
    return f"TASK-{problem.name}-cp{numero}"


def build_task_contract(
    problem: ScbProblem, checkpoint: str, prompt: str, entry_file: str
) -> dict:
    """Monta o contrato de task (JSON) gravado em `coder/tasks/`.

    Quem julga a correção é o avaliador oficial do SlopCodeBench, não estes
    critérios — eles só orientam o coder.
    """
    return {
        "id": task_id_for(problem, checkpoint),
        "description": prompt,
        "acceptance_criteria": [
            f"O programa é executável a partir de `{entry_file}` na raiz do workspace.",
            "O comportamento respeita integralmente a especificação do checkpoint.",
        ],
        "contract": {
            "tech_stack": "python",
            "product_type": "cli",
            "entry_file": entry_file,
            "checkpoint": checkpoint,
        },
    }


def build_coder_message(checkpoint: str, prompt: str, entry_file: str) -> str:
    """Monta a mensagem de entrada do coder (o "contrato" da sessão).

    Emula a saída do context_engineer: fixa stack/produto e injeta as regras que
    garantem um artefato avaliável. O enunciado em si é o prompt oficial,
    entregue sem alteração.
    """
    return f"""# CONTRATO DE EXECUÇÃO (benchmark SlopCodeBench — {checkpoint})

## Stack e produto
- `tech_stack`: Python 3.12.
- `product_type`: cli.

## Regras OBRIGATÓRIAS do benchmark (sobrepõem-se a qualquer default)
1. O ponto de entrada do programa é `{entry_file}`, na RAIZ do seu workspace.
2. Declare TODAS as dependências de terceiros em `requirements.txt`, na raiz.
   O avaliador instala esse arquivo sozinho; você não precisa (nem consegue)
   criar o ambiente virtual.
3. A avaliação usa testes próprios e ocultos, que incluem os checkpoints
   anteriores. Não quebre o que já funcionava.

## Tarefa
{prompt.strip()}

Entregue o código agora, persistindo os arquivos via `tool_criar_arquivo`.
"""
