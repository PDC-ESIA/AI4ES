"""Tradução de uma instância SWE-bench para o que o loop consome.

Dois artefatos por instância, no mesmo papel que o `context_engineer` cumpre no
pipeline completo (ele fica fora do benchmark):

1. **Task** (`TASK-001.json`): gravada em `coder/tasks/`, lida pelo harness do
   executor (critérios de aceite, contrato) e referenciada no `state["tasks"]`.
2. **Mensagem de entrada**: o "contrato" da sessão entregue ao coder — o texto
   do issue, as regras do ambiente preparado pelo benchmark e como declarar os
   testes no `run.json`.

REGRA DE OURO — nada do gabarito sai daqui. `patch`, `test_patch`,
`FAIL_TO_PASS`, `PASS_TO_PASS`, `hints_text` e o `eval_script` do dataset nunca
entram na task nem na mensagem. As dicas de comando de teste por repositório
(`TEST_COMMAND_HINTS`) trazem só a SINTAXE do executor de testes daquele
projeto, nunca os alvos. O teste de vazamento está em `test_contract.py`.

Os critérios de aceite são fixos e iguais para toda instância: a regra é
documentada e não varia com o issue. Eles NÃO decidem a aprovação — o
`implementation_validator` aprova pelo status técnico do harness — e servem ao
registro, como na produção.
"""

from __future__ import annotations

from .dataset import SWEInstance

# Id de task aceito pelo harness/TaskIterator (`^TASK-[0-9]+$`).
TASK_ID = "TASK-001"

# Sintaxe do executor de testes de cada projeto, extraída do `eval_script` do
# próprio dataset SEM os alvos. Repositórios ausentes usam o pytest.
_PYTEST_HINT = "python -m pytest -rA <arquivo_de_teste.py>"
TEST_COMMAND_HINTS: dict[str, str] = {
    "django/django": (
        "python tests/runtests.py --verbosity 2 --settings=test_sqlite "
        "--parallel 1 <app_de_teste>"
    ),
    "sympy/sympy": "python bin/test -C --verbose <arquivo_de_teste.py>",
}
# Observação que acompanha a sintaxe, fora do trecho de código.
_TEST_COMMAND_NOTES: dict[str, str] = {
    "django/django": (
        "  `<app_de_teste>` é o rótulo de um app/módulo em `tests/` "
        "(ex.: `admin_views` ou `i18n.tests`).\n"
    ),
}

ACCEPTANCE_CRITERIA: tuple[dict, ...] = (
    {
        "id": "CA-01",
        "description": (
            "O comportamento incorreto relatado no issue deixa de ocorrer: o "
            "código do repositório passa a se comportar como o issue espera."
        ),
        "automatable": True,
    },
    {
        "id": "CA-02",
        "description": (
            "Os testes existentes das partes alteradas continuam passando "
            "(nenhuma regressão)."
        ),
        "automatable": True,
    },
)


def suggested_test_command(repo: str) -> str:
    """Sintaxe sugerida para rodar testes no repositório (sem alvos)."""
    return TEST_COMMAND_HINTS.get(repo, _PYTEST_HINT)


def build_task_contract(instance: SWEInstance) -> dict:
    """Task no formato do `context_engineer` (ver `context_engineer/schemas.py`)."""
    return {
        "id": TASK_ID,
        "type": "component",
        "complexity": "medium",
        "description": (
            f"Corrigir, no repositório existente `{instance.repo}`, o problema "
            "relatado no issue abaixo, sem quebrar o comportamento existente.\n\n"
            f"{instance.problem_statement.strip()}"
        ),
        "business_rules": [
            "O repositório já existe: altere o código atual, não recrie o projeto.",
            "Preserve a API pública existente (assinaturas e comportamento "
            "não relacionados ao issue).",
        ],
        "acceptance_criteria": [dict(criterio) for criterio in ACCEPTANCE_CRITERIA],
        "contract": {
            "inputs": [],
            "outputs": [],
            "interfaces": ["API pública existente do repositório"],
        },
        "requirement_id": instance.instance_id,
        "requirement_refs": [],
        "design_refs": [],
    }


def build_coder_message(instance: SWEInstance) -> str:
    """Mensagem de entrada do coder: o issue + as regras do benchmark."""
    return f"""# CONTRATO DE EXECUÇÃO (benchmark SWE-bench Verified)

## Contexto
Você vai trabalhar num repositório EXISTENTE: `{instance.repo}` (versão
{instance.version}). Ele já está no seu workspace, no estado imediatamente
anterior à correção de um issue real. Não é um projeto novo: NÃO existe
`PLAN.md` e você NÃO deve criar um.

## Issue a resolver (texto original)
<issue>
{instance.problem_statement.strip()}
</issue>

## Sua tarefa
Altere o código-fonte do repositório para que o problema descrito no issue
deixe de ocorrer, sem quebrar o comportamento existente. A task
correspondente está em `coder/tasks/{TASK_ID}.json`.

## Como trabalhar num repositório grande
1. Navegue pelas pastas com `tool_listar_workspace` e leia os arquivos
   relevantes com `tool_ler_arquivo`.
2. Edite arquivos EXISTENTES com `tool_substituir_trecho`, em trechos pontuais.
   NÃO reescreva um arquivo existente inteiro com `tool_criar_arquivo`.
3. Você pode escrever testes para o comportamento corrigido.

## Regras OBRIGATÓRIAS do benchmark (sobrepõem-se às suas regras padrão)
- O ambiente de execução JÁ está pronto: o benchmark preparou `Dockerfile`,
  `.dockerignore` e `run.json`. O Executor roda os seus comandos DENTRO de um
  container com todas as dependências do repositório já instaladas.
- NÃO crie virtualenv, NÃO instale dependências e NÃO use `venv/bin/...`: use
  `python` diretamente — ele já é o interpretador do ambiente do projeto.
  Única exceção: se você alterar código COMPILADO (C/Cython), declare no
  `build` a recompilação do próprio projeto:
  `python -m pip install -e . --no-deps --no-build-isolation`.
- NÃO altere nem remova `Dockerfile` e `.dockerignore`. No `run.json`, mantenha
  `"sandbox": "docker"` e `"surface": "none"`.
- Os comandos rodam a partir da raiz do repositório. Cada comando de teste tem
  limite de 120 segundos: rode APENAS os testes relacionados ao que você
  alterou, nunca a suíte inteira.
- Declare no campo `test` do `run.json` os comandos que exercitam a sua
  correção. Sintaxe deste repositório:
  `{suggested_test_command(instance.repo)}`
{_TEST_COMMAND_NOTES.get(instance.repo, "")}- O campo `acceptance_tests` do `run.json` é opcional aqui (pode ficar `{{}}`).

## Entrega
Faça as alterações AGORA, persistindo tudo pelas ferramentas, e atualize o
campo `test` do `run.json`. Ao terminar, responda com um resumo curto do que
mudou.
"""
