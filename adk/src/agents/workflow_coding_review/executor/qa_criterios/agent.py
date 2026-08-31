"""Agente de QA de critérios de aceite — escreve os testes, não os julga.

Construído com `LlmAgent` direto, e NÃO com `create_se_agent`, por causa do
GAP-00 já documentado no `implementation_validator`: no ADK, `output_schema`
ativa decodificação restrita e desabilita function calling, enquanto a factory
sempre injeta ao menos uma tool. Este agente não precisa de tool nenhuma — tudo
o que ele precisa saber (critérios, URL, HTML da página) chega no prompt — então
trocar a factory por `LlmAgent` compra saída estruturada garantida sem perder
nada.

O agente é invocado por CÓDIGO (ver `verificacao.py`), não por outro LLM. Essa é
a diferença que faz o QA entrar no loop de forma previsível: quem decide se ele
roda é a mesma política determinística que decide o resto do loop, e não a
disposição de um modelo em chamar uma tool.
"""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent

from . import prompt
from .schemas import EspecificacaoCriterios

_DEFAULT_MODEL = "gemini-2.5-flash"

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="qa_criterios_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_schema=EspecificacaoCriterios,
    output_key="qa_especificacao",
)

root_agent = agent
