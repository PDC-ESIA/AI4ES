"""Coder dedicado ao workflow HumanEval.

Agente simplificado: recebe assinatura+docstring de função Python,
implementa a função e grava em solution.py. Sem Docker, sem FastAPI,
sem PLAN.md — foco exclusivo em corretude algorítmica.
"""

import os

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

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

_WORKSPACE_ROOT = str(get_workspace_root())
_CODER_WS = str(get_agent_workspace("he_coder"))


def _bind(tool):
    return _bind_tool_to_workspace(tool, _CODER_WS, _WORKSPACE_ROOT)


_INSTRUCTION = f"""
# PERFIL
Você é um programador Python expert especializado em algoritmos e estruturas
de dados. Sua tarefa é implementar UMA função Python a partir de uma assinatura
e docstring fornecidas.

# MODO DE OPERAÇÃO
Você opera dentro de um LOOP junto com um Executor que roda pytest no seu código.

## Primeira execução (campo execution_result AUSENTE):
Analise a assinatura e a docstring. Implemente a função completa e correta.
Grave o resultado via `tool_criar_arquivo("solution.py", conteudo)`.

## Re-execução após falha (campo execution_result PRESENTE):
O Executor detectou falha nos testes. Analise o erro e corrija a implementação.

--- RESULTADO DA EXECUÇÃO ANTERIOR ---
{{{{execution_result?}}}}
--- FIM DO RESULTADO ---

# REGRAS
1. Grave APENAS o arquivo `solution.py` via `tool_criar_arquivo`.
2. O arquivo DEVE conter a função com a assinatura EXATA fornecida no prompt.
3. Inclua todos os imports necessários NO TOPO do arquivo.
4. NÃO crie Dockerfile, docker-compose, README ou qualquer outro arquivo.
5. NÃO descreva o que vai fazer — FAÇA chamando tool_criar_arquivo.
6. Após gravar, produza texto curto confirmando o que foi implementado.

# WORKSPACE
Seu diretório de trabalho é `{_CODER_WS}/`.
Use caminhos RELATIVOS (ex: `solution.py`).

# FERRAMENTAS DISPONÍVEIS
- `tool_criar_arquivo(caminho, conteudo)`: cria/sobrescreve arquivo.
- `tool_ler_arquivo(caminho)`: lê arquivo existente.
- `tool_substituir_trecho(caminho, trecho_antigo, trecho_novo)`: edita trecho.
"""

agent = LlmAgent(
    model=_model,
    name="he_coder_agent",
    description="Implementa função Python a partir de assinatura+docstring (HumanEval).",
    instruction=_INSTRUCTION,
    output_key="implementation",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=8192,
    ),
    tools=[
        _bind(FunctionTool(tool_criar_arquivo)),
        _bind(FunctionTool(tool_ler_arquivo)),
        _bind(FunctionTool(tool_substituir_trecho)),
    ],
)
