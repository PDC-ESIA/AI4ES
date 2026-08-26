"""Camada 3 (evals, escopo coder_isolado): avaliação de qualidade do cr_review_analyzer.

Diferente das Camadas 1/2 (100% determinísticas, LLM sempre stubado), estes
testes rodam o `cr_review_analyzer` de PRODUÇÃO — o `LlmAgent` real usado em
`workflow_coding_review.reviewer.agent`, sem substituir `before_model_callback`
nem mockar a resposta — contra o provider de LLM real configurado no projeto
(GitHub Copilot via LiteLLM, ver `.env`/`ADK_LLM_MODEL`). O objetivo é
responder "o reviewer de produção detecta problemas reais de qualidade?",
uma pergunta que nenhum teste das Camadas 1/2 responde (lá o LLM nunca é
chamado de verdade).

Estrutura: um único teste PARAMETRIZADO (`test_reviewer_contra_dataset`)
roda contra um dataset curado de 12 casos de referência
(`tests/coder_isolado/evals/dataset/*.json` — ver `dataset/README.md` para
o schema e como adicionar casos), cada um checado em 2 camadas:

1. **Determinística** (barata): confere `## Status: <esperado>` e, para
   casos BLOQUEADO, que a seção `## Issues` contém pelo menos uma das
   `palavras_chave_deterministicas` do caso. Roda primeiro — se falhar,
   o teste já falha aqui, sem gastar a camada 2.
2. **LLM-judge** (mais cara): um segundo `LlmAgent`, construído localmente
   só para este teste (não é agente de produção), avalia semanticamente
   se a saída do reviewer capturou a ESSÊNCIA do problema esperado do
   caso — pega falsos positivos que a checagem de palavra-chave sozinha
   deixaria passar (ex.: reviewer bloqueou pelo motivo ERRADO).

Implicações práticas:
- **Skip automático** se não houver credencial real disponível (fixture
  `_requer_llm_real`, de `tests/coder_isolado/conftest.py`) — não falha,
  só pula, para não quebrar quem não tem `python adk/scripts/copilot_auth.py`
  rodado localmente.
- **Custo real de API**: até 2 chamadas de LLM por caso (1 reviewer + 1
  judge condicional, só se a camada determinística já passou) — com os 12
  casos do dataset, uma varredura completa pode chegar a ~24 chamadas.
  Por isso **não roda no CI padrão**, só sob demanda ou num job nightly
  separado; rodar caso a caso via `-k <id_do_caso>` para validar mudanças
  pontuais sem gastar a varredura inteira.
- Marcados com `@pytest.mark.evals` explicitamente, além do marker
  automático já aplicado pelo hook de pasta em `tests/conftest.py`
  (`tests/coder_isolado/evals/` → `coder_isolado` + `evals`) — a
  redundância é proposital: com custo real de API envolvido, o marker
  deve ser óbvio lendo só o teste, sem precisar checar o hook.
- A saída real do `cr_review_analyzer` é **markdown livre**
  (`## Status: APROVADO|BLOQUEADO`, `## Issues`, `## Resumo`), não JSON
  validável contra `ReviewOutput` — a camada determinística faz parsing
  de texto, não `ReviewOutput.model_validate(...)` (ver investigação
  prévia: o schema Pydantic existe mas não é o formato de saída usado em
  produção).
"""

from __future__ import annotations

import importlib
import re

import pytest
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from .conftest import carregar_casos_dataset


async def _rodar_reviewer(mensagem: str = "Revise o código do workspace.") -> str:
    """Recarrega o reviewer contra o `WORKSPACE_OUTPUT_DIR` do teste e roda via Runner real.

    `_CODER_WS`/`_REVIEW_WS` são constantes calculadas na importação de
    `review_tools.py`/`reviewer/agent.py` — como o conftest global já
    pré-importa esses módulos (contra o workspace default, antes de
    qualquer `monkeypatch.setenv`), é preciso `importlib.reload` nos dois,
    NESSA ordem, para religar as constantes ao workspace isolado deste
    teste. Mesmo padrão de
    `tests/coder_isolado/infraestrutura/test_review_agent_persistence.py`.
    """
    from shared.tools.coding_tools import review_tools

    importlib.reload(review_tools)
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(cr_reviewer)

    runner = Runner(
        app_name="cr_reviewer_eval",
        agent=cr_reviewer.agent,
        session_service=InMemorySessionService(),
    )
    session = await runner.session_service.create_session(
        app_name="cr_reviewer_eval", user_id="u", state={},
    )
    msg = types.Content(role="user", parts=[types.Part.from_text(text=mensagem)])
    eventos = [
        e async for e in runner.run_async(
            user_id="u", session_id=session.id, new_message=msg,
        )
    ]
    await runner.close()

    textos = [
        p.text for e in eventos if e.content
        for p in e.content.parts if p.text
    ]
    return "\n".join(textos)


def _secao_issues(saida: str) -> str:
    """Extrai o texto sob o heading `## Issues` até o próximo `##` (ou fim)."""
    match = re.search(r"##\s*Issues\s*\n(.*?)(?=\n##\s|\Z)", saida, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""


@pytest.mark.evals
@pytest.mark.timeout(240)
@pytest.mark.asyncio
@pytest.mark.parametrize("caso", carregar_casos_dataset(), ids=lambda c: c["id"])
async def test_reviewer_contra_dataset(caso, _requer_llm_real, coder_workspace_com_codigo, _llm_judge):
    """Roda o reviewer real contra um caso do dataset e checa em 2 camadas.

    Camada 1 (determinística, barata): `## Status: <esperado>` e, se
    BLOQUEADO, pelo menos uma palavra-chave esperada na seção `## Issues`.
    Falha rápido aqui sem gastar o judge.

    Camada 2 (LLM-judge, mais cara): só roda se a Camada 1 já passou.
    Avalia semanticamente se a saída do reviewer capturou a essência do
    `problema_para_judge` do caso — pega o caso em que o reviewer acertou
    o veredito e a palavra-chave "por acidente", mas não pelo motivo certo.
    """
    coder_workspace_com_codigo({**caso["arquivos"], **caso.get("arquivos_teste", {})})

    saida = await _rodar_reviewer()

    # Camada 1: checagem determinística (barata) — falha rápido sem gastar o judge
    status_esperado = f"## Status: {caso['veredito_esperado']}"
    assert status_esperado in saida, (
        f"[{caso['id']}] Esperava {caso['veredito_esperado']}. Saída:\n{saida}"
    )
    if caso["veredito_esperado"] == "BLOQUEADO":
        issues = _secao_issues(saida)
        assert issues, f"[{caso['id']}] Seção '## Issues' ausente:\n{saida}"
        assert any(
            re.search(kw, issues, re.IGNORECASE)
            for kw in caso["palavras_chave_deterministicas"]
        ), f"[{caso['id']}] Nenhuma palavra-chave esperada encontrada em:\n{issues}"

    # Camada 2: LLM-judge (mais caro) — só roda se a Camada 1 já passou
    veredito = await _llm_judge(
        problema_esperado=caso["problema_para_judge"],
        saida_reviewer=saida,
    )
    assert veredito.correto, (
        f"[{caso['id']}] Judge discordou da avaliação do reviewer.\n"
        f"Problema esperado: {caso['problema_para_judge']}\n"
        f"Justificativa do judge: {veredito.justificativa}\n"
        f"Saída do reviewer:\n{saida}"
    )
