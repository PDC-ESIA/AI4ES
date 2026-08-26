"""Camada 4 (sandbox e2e, escopo coder_isolado): pipeline workflow_coding_review completo, com LLM real.

Roda o `root_agent` de PRODUÇÃO de `workflow_coding_review` ponta a ponta —
`context_engineer` → loop `[coder ↔ executor]` (com execução REAL de código
via `DirectSandbox`, subprocess de verdade, não mockado) → `reviewer` — contra
o provider de LLM real configurado no projeto (GitHub Copilot via LiteLLM).

Mais caro e lento que a Camada 3 (evals/, que roda só o reviewer isolado):
até ~12 chamadas de LLM no pior caso (1 context_engineer + até 5 iterações
do loop coder/executor, cada iteração podendo custar 2 chamadas — coder e o
validador embutido como AgentTool no executor — + 1 reviewer), na faixa de
alguns minutos. Por isso:

- **Skip automático** sem credencial real (fixture `_requer_llm_real`).
- `@pytest.mark.timeout(900)` (15min) por teste.
- **Não roda no CI padrão** — sob demanda/nightly, mesmo racional da
  Camada 3.
- Marcados com `@pytest.mark.sandbox` explicitamente, além do marker
  automático do hook de pasta.

⚠️ **Bug de ambiente conhecido (Windows local, não corrigido aqui)**:
`shared/execution/sandbox.py` (`DirectSandbox`, usado pelo executor para
rodar o código gerado de verdade) importa o módulo `resource` e usa
`subprocess.run(..., preexec_fn=...)` — ambos POSIX-only. Em Windows local
isso quebra na importação (`ModuleNotFoundError: No module named 'resource'`)
MUITO antes de qualquer chamada de LLM acontecer — inclusive quebra a
importação de `tests/conftest.py` (pré-cache global), então hoje a suite
inteira falha a coletar em Windows local, não só estes 2 testes. Isso é
esperado neste ambiente e não é uma falha do teste em si nem do LLM — não
tente mascarar rodando com um provider/skip diferente; é um bug de
portabilidade real, já reportado separadamente, cuja correção está fora do
escopo desta tarefa.
"""

from __future__ import annotations

import importlib
import sys

import pytest
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types


def _reconstruir_pipeline_producao():
    """Reconstrói `workflow_coding_review.agent.agent` do zero, contra o workspace do teste.

    Duas razões distintas, ambas obrigatórias — não é só "recarregar por
    garantia":

    1. **Workspace**: `coder/agent.py` e `reviewer/agent.py` (via
       `review_tools.py`) calculam caminhos (`_CODER_WS`, `_REVIEW_WS`,
       `_WORKSPACE_ROOT`) no momento do IMPORT do módulo. O pré-cache do
       conftest global já importou a árvore inteira uma vez, contra o
       workspace default — sem reload, essas constantes ficariam presas
       lá, não no `workspace_fixture` deste teste. `context_engineer` e
       `executor` resolvem caminhos em tempo de CHAMADA (de propósito —
       ver docstring de `executor/agent.py`), então não têm essa parte do
       problema.
    2. **`parent_agent` só pode ser setado uma vez**: a ADK
       (`google.adk.agents.base_agent.BaseAgent`) proíbe compor a MESMA
       instância de agente como sub_agent duas vezes — levanta
       `ValueError` na 2ª tentativa (confirmado lendo
       `BaseAgent.__set_parent_agent_for_sub_agents`, chamado no
       `model_post_init` de todo `SequentialAgent`/`LoopAgent`). Como
       `context_engineer.agent` e `executor.agent` já foram compostos no
       pipeline construído pelo pré-cache do conftest global, PRECISAM
       de reload aqui só para virar instâncias novas e sem parent — nada
       a ver com workspace.

    Ordem importa:
    - `review_tools` reload ANTES de `reviewer.agent` (que importa
      `_CODER_WS` de lá por valor no momento do import, não por
      referência viva — reload de `reviewer.agent` sem antes recarregar
      `review_tools` pegaria o valor antigo).
    - `context_engineer.agent`/`coder.agent` (submódulo) ANTES do pacote
      `context_engineer`/`coder` (`__init__.py` faz `from .agent import
      agent` — precisa recarregar o pacote para "ver" o submódulo já
      atualizado). `executor`/`reviewer` NÃO têm esse passo extra: os
      `__init__.py` deles evitam de propósito o re-export
      `from .agent import agent` exatamente para não quebrar
      `importlib.reload` em teste (ver docstring de
      `executor/__init__.py`/`reviewer/__init__.py`).
    - `workflow_coding_review.agent` (top-level) por último, para
      reconstruir o `LoopAgent`/`SequentialAgent` a partir de todos os
      sub-agentes já renovados.

    **Achado real, validado em execução** (script descartável, rodado 2x
    seguidas na mesma sessão simulando os 2 testes deste arquivo, com o
    shim local de `resource` ativo): a hipótese original sobre
    `parent_agent`/`AgentTool` do `implementation_validator` (usado como
    `AgentTool` dentro do executor) **não se confirmou como problema** —
    `parent_agent` é resetado corretamente em ambas as construções, sem
    `ValueError`, para todos os sub-agentes (incluindo os que passam pelo
    `AgentTool`, que nunca seta `parent_agent` — só guarda `self.agent`).

    O bug real encontrado foi outro, mais básico: `context_engineer/__init__.py`
    e `coder/__init__.py` fazem `from .agent import agent` — isso sombreia
    o atributo `<pacote>.agent` com a instância `LlmAgent`, não o
    submódulo. `import ...context_engineer.agent as X` resolve por
    travessia de atributo do pacote (pega o `LlmAgent` sombreado), não por
    `sys.modules` (que tem o módulo de verdade) — o resultado era
    `TypeError: reload() argument must be a module`, não a `ValueError`
    de `parent_agent` esperada. Por isso o acesso a esses 2 módulos
    (só eles — `executor`/`reviewer` não têm esse re-export) é via
    `sys.modules[...]` direto, não `import ... as X`.

    Pré-condição do `sys.modules[...]`: o submódulo precisa já ter sido
    importado alguma vez antes (`KeyError` caso contrário) — garantido
    pelo pré-cache de `tests/conftest.py`, que importa a árvore inteira
    de `workflow_coding_review` antes de qualquer teste rodar.
    """
    from shared.tools.coding_tools import review_tools

    importlib.reload(review_tools)

    ce_agent_mod = sys.modules["src.agents.workflow_coding_review.context_engineer.agent"]
    importlib.reload(ce_agent_mod)
    import src.agents.workflow_coding_review.context_engineer as ce_pkg

    importlib.reload(ce_pkg)

    coder_agent_mod = sys.modules["src.agents.workflow_coding_review.coder.agent"]
    importlib.reload(coder_agent_mod)
    import src.agents.workflow_coding_review.coder as coder_pkg

    importlib.reload(coder_pkg)

    import src.agents.workflow_coding_review.executor.agent as executor_agent_mod

    importlib.reload(executor_agent_mod)

    import src.agents.workflow_coding_review.reviewer.agent as reviewer_agent_mod

    importlib.reload(reviewer_agent_mod)

    import src.agents.workflow_coding_review.agent as pipeline_mod

    importlib.reload(pipeline_mod)

    return pipeline_mod.agent


async def _rodar_pipeline(mensagem: str) -> list:
    """Roda o pipeline reconstruído via Runner real, mesmo padrão de `test_hitl_e2e.py`."""
    pipeline = _reconstruir_pipeline_producao()

    runner = Runner(
        app_name="coding_review_pipeline_e2e",
        agent=pipeline,
        session_service=InMemorySessionService(),
    )
    session = await runner.session_service.create_session(
        app_name="coding_review_pipeline_e2e", user_id="u", state={},
    )
    msg = types.Content(role="user", parts=[types.Part.from_text(text=mensagem)])
    eventos = [
        e async for e in runner.run_async(
            user_id="u", session_id=session.id, new_message=msg,
        )
    ]
    await runner.close()
    return eventos


def _reviewer_participou(eventos: list) -> bool:
    """True se algum evento veio do reviewer (`cr_review_analyzer`)."""
    return any("review" in (e.author or "").lower() for e in eventos)


@pytest.mark.sandbox
@pytest.mark.timeout(900)
@pytest.mark.asyncio
async def test_pipeline_completo_converge_e_aprova(
    _requer_llm_real, workspace_fixture, seed_requirements_e_design,
):
    """Smoke e2e: tarefa simples o bastante para o coder acertar de primeira (ou quase).

    Foco: "o pipeline converge e produz um veredito" — NÃO "o veredito foi
    X". LLM real é não-determinístico; travar o assert num resultado
    específico (ex.: sempre APROVADO) tornaria o teste flaky por design.
    """
    seed_requirements_e_design(
        workspace_fixture,
        texto_rf=(
            "# RF-001 — Soma de dois inteiros\n\n"
            "O sistema deve expor uma função `somar(a: int, b: int) -> int` "
            "que retorna a soma dos dois argumentos. Deve ser acompanhada de "
            "testes automatizados cobrindo pelo menos o caso feliz.\n\n"
            "Superfície: script Python simples (comando), sem servidor HTTP.\n"
        ),
        texto_design=(
            "# Análise Técnica — RF-001\n\n"
            "Implementar `somar(a, b)` em um único módulo Python "
            "(ex.: `soma.py`), com type hints. Testes via `pytest`. Não há "
            "componente de rede/serviço — execução via linha de comando.\n"
        ),
    )

    eventos = await _rodar_pipeline(
        "Implemente o RF-001 (soma de dois inteiros) conforme os artefatos do workspace."
    )

    assert eventos, "Runner não emitiu nenhum evento"
    assert _reviewer_participou(eventos), (
        "Pipeline não chegou a invocar o reviewer — trajetória de autores: "
        f"{[e.author for e in eventos]}"
    )
    # Reporta o resultado real para inspeção manual, sem travar o assert nele.
    textos = [
        p.text for e in eventos if e.content
        for p in e.content.parts if p.text
    ]
    print("\n--- Saída completa do pipeline (informativo, não asserido) ---")
    print("\n".join(textos))


@pytest.mark.sandbox
@pytest.mark.timeout(900)
@pytest.mark.asyncio
async def test_pipeline_completo_ciclo_falha_e_corrige(
    _requer_llm_real, workspace_fixture, seed_requirements_e_design,
):
    """Smoke e2e do ciclo de correção — requisito sutil, chance razoável de 1ª tentativa falhar.

    Sem garantia: LLM real pode acertar de primeira. O foco deste teste é
    "o ciclo funciona ponta a ponta com LLM real quando um retry acontece",
    não forçar deterministicamente uma falha. Assert: o pipeline termina
    (converge antes do teto OU encerra controladamente nele) sem lançar
    exception não tratada — o próprio `LoopAgent` já garante isso
    estruturalmente (coberto contra stub em
    `tests/coder_isolado/trajetoria/test_trajetoria_convergencia_loop.py`);
    aqui a pergunta é se isso continua verdade com comportamento real de
    LLM, não mockado.
    """
    seed_requirements_e_design(
        workspace_fixture,
        texto_rf=(
            "# RF-002 — Verificação de palíndromo\n\n"
            "O sistema deve expor uma função `eh_palindromo(texto: str) -> bool` "
            "que verifica se `texto` é um palíndromo, IGNORANDO diferenças de "
            "maiúsculas/minúsculas E espaços em branco (ex.: "
            "'A man a plan a canal Panama' deve ser considerado palíndromo). "
            "Deve haver testes automatizados cobrindo explicitamente esse "
            "caso com espaços e mistura de maiúsculas/minúsculas, não só "
            "palavras únicas em minúsculas.\n\n"
            "Superfície: script Python simples (comando), sem servidor HTTP.\n"
        ),
        texto_design=(
            "# Análise Técnica — RF-002\n\n"
            "Implementar `eh_palindromo(texto)` em um único módulo Python "
            "(ex.: `palindromo.py`), com type hints. Normalizar o texto "
            "(remover espaços, normalizar caixa) antes de comparar com o "
            "reverso. Testes via `pytest`, incluindo o caso com espaços e "
            "maiúsculas. Não há componente de rede/serviço.\n"
        ),
    )

    eventos = await _rodar_pipeline(
        "Implemente o RF-002 (verificação de palíndromo) conforme os artefatos do workspace."
    )

    assert eventos, "Runner não emitiu nenhum evento"

    autores_executor = [e.author for e in eventos if e.author == "cr_executor_agent"]
    assert len(autores_executor) <= 5, (
        f"Executor rodou {len(autores_executor)} vezes — acima do "
        f"max_iterations=5 do LoopAgent (_code_execute_loop)."
    )

    assert _reviewer_participou(eventos), (
        "Pipeline não chegou a invocar o reviewer — trajetória de autores: "
        f"{[e.author for e in eventos]}"
    )
    print(f"\n--- Executor rodou {len(autores_executor)}x neste run (informativo) ---")
