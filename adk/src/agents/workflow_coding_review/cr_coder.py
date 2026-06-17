"""Coder dedicado ao workflow coding_review.

Instância ajustada do coder original (src/agents/coder/):
- Prompt composto a partir do canônico, sem seções de Git/HITL.
- Tools de filesystem bound a workspace_output/coder/src/ (consolidado).
- Evita conflito de parent com o sdlc_pipeline (instância dedicada).
"""

import os
import re

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from shared.agent_factory import _bind_tool_to_workspace
from shared.workspace import get_agent_workspace, get_workspace_root
from shared.tools import (
    tool_criar_arquivo,
    tool_ler_arquivo,
    tool_substituir_trecho,
)
from src.agents.coder import prompt as coder_prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

_WORKSPACE_ROOT = str(get_workspace_root())
_CODER_WS = str(get_agent_workspace("cr_coder"))


def _bind(tool):
    return _bind_tool_to_workspace(tool, _CODER_WS, _WORKSPACE_ROOT)


# ---------------------------------------------------------------------------
# Composição do prompt: split por headers, exclui seções de Git/HITL,
# adiciona seções de WORKSPACE + FERRAMENTAS específicas deste pipeline.
# ---------------------------------------------------------------------------

_EXCLUDE_HEADERS = {
    "PADRÃO DE COMMITS E BRANCHES",
    "FLUXO DE TRABALHO SEQUENCIAL",
    "FORMATO DE SAÍDA DE CÓDIGO",
    "LEMBRETE FINAL",
    "REGRA CRÍTICA DE EXECUÇÃO",
}


def _build_instruction() -> str:
    """Compõe a instrução do coder a partir do prompt canônico, sem git/HITL."""
    sections = re.split(r"(?=^# )", coder_prompt.instruction.strip(), flags=re.MULTILINE)

    kept = []
    for section in sections:
        header_match = re.match(r"^# (.+)", section)
        if header_match:
            title = header_match.group(1).strip()
            if any(title.startswith(exc) for exc in _EXCLUDE_HEADERS):
                continue
        kept.append(section)

    # Ajuste 1: PERFIL DO AGENTE — remover menção a git
    composed = "\n".join(kept)
    composed = composed.replace(
        "código altamente modular e gerenciar o controle de versão (Git).",
        "código altamente modular.",
    )

    # Ajuste 2: CHAIN OF THOUGHT — remover item "Estratégia Git"
    composed = re.sub(
        r"\n\s*3\.\s*Estratégia Git:.*?(?=\n</thinking>)",
        "",
        composed,
        flags=re.DOTALL,
    )

    # Ajuste 3: CHAIN OF THOUGHT — remover "ou Git" da introdução
    composed = composed.replace(
        "qualquer capacidade de código ou Git:",
        "qualquer capacidade de código:",
    )

    # Seções adicionais: WORKSPACE + FERRAMENTAS + SAÍDA FINAL
    workspace_section = f"""

# WORKSPACE
Seu diretório de trabalho é `{_CODER_WS}/`.
Use caminhos RELATIVOS (ex: `app/main.py`, `tests/test_x.py`).
NÃO USE git, NÃO crie branches, NÃO faça commits — essas ferramentas não existem.

# FERRAMENTAS DISPONÍVEIS (APENAS ESTAS — não invente outras)
- `tool_criar_arquivo(caminho, conteudo)`: cria/sobrescreve arquivo (caminho relativo).
- `tool_ler_arquivo(caminho)`: lê arquivo já existente no workspace.
- `tool_substituir_trecho(caminho, trecho_antigo, trecho_novo)`: edita trecho de arquivo existente.

# REGRA CRÍTICA — PERSISTÊNCIA OBRIGATÓRIA VIA TOOLS
Você DEVE chamar `tool_criar_arquivo` para CADA arquivo que implementar.
Código escrito apenas na resposta de texto (ex: blocos markdown, XML) NÃO é
salvo em disco e será PERDIDO. A ÚNICA forma de persistir código é via
`tool_criar_arquivo`.

Chame UMA tool por vez (o framework não suporta chamadas paralelas).
Após receber o resultado de cada tool, chame a próxima na mensagem seguinte.

# REGRA DE COMPLETUDE — NÃO PARE APÓS O PRIMEIRO ARQUIVO
Você DEVE implementar o projeto COMPLETO em uma única sessão. Isso inclui:
- Modelos / schemas
- Rotas / endpoints
- Templates / frontend (se aplicável)
- Testes unitários
- Arquivos auxiliares (__init__.py, conftest.py, requirements.txt, etc.)

NÃO produza texto descritivo entre os arquivos. NÃO diga "Próximo passo".
NÃO descreva o que vai fazer — FAÇA chamando tool_criar_arquivo.
Continue chamando tools até que TODOS os arquivos necessários estejam criados.
Só produza texto final quando não houver mais arquivos a criar.

# SAÍDA FINAL
Somente após criar TODOS os arquivos via tools, produza um texto curto (não JSON)
com a lista final dos arquivos criados + breve descrição de cada um.
Sem perguntas, sem menção a "próximos passos", sem dúvidas.
"""
    return composed + workspace_section


_INSTRUCTION = _build_instruction()

agent = LlmAgent(
    model=_model,
    name="cr_coder_agent",
    description="Implementa código funcional a partir de requisitos, sem git.",
    instruction=_INSTRUCTION,
    output_key="implementation",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
    tools=[
        _bind(FunctionTool(tool_criar_arquivo)),
        _bind(FunctionTool(tool_ler_arquivo)),
        _bind(FunctionTool(tool_substituir_trecho)),
    ],
)
