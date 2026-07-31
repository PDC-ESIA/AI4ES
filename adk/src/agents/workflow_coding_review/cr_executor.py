"""Executor dedicado ao workflow coding_review.

Agente responsável UNICAMENTE por executar o código produzido pelo coder
em um container Docker isolado. Não modifica código — apenas:

1. Lê os arquivos do workspace do coder (coder/src/).
2. Usa o Dockerfile do coder (ou gera fallback se ausente).
3. Builda a imagem e roda o container com timeout.
4. Captura stdout/stderr e persiste relatório em coder/execution/.
5. Se SUCESSO → chama exit_loop (encerra o LoopAgent externo).
   Se FALHA → reporta resultado com logs (o loop volta ao coder).

Este agente vive DENTRO de um LoopAgent junto com o coder:
    LoopAgent [coder → executor]
Quando o executor chama exit_loop(), o loop para e o pipeline segue.

As tools de execução Docker (build, run, healthcheck) e seus helpers vivem
em shared/tools/coding_review/docker_executor.py.
"""

import os
import textwrap

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from shared.tools.coding_review.docker_executor import (
    _CODER_WS,
    _EXEC_WS,
    _HOST_PORT,
    _detect_entrypoint,
    _detect_requirements,
    _discover_main_route,
    _generate_dockerfile,
    _has_pyproject,
    tool_executar_em_docker,
    tool_exit_loop_se_sucesso,
    tool_listar_arquivos_coder,
    tool_verificar_docker,
)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

# Re-exportados para uso/teste via atributo do módulo (ex.: cr_executor._CODER_WS,
# cr_executor._detect_entrypoint) — mantém compatibilidade com quem já referenciava
# esses nomes diretamente neste módulo antes da extração para docker_executor.py.
__all__ = [
    "agent",
    "_CODER_WS",
    "_EXEC_WS",
    "_HOST_PORT",
    "_detect_entrypoint",
    "_detect_requirements",
    "_discover_main_route",
    "_generate_dockerfile",
    "_has_pyproject",
    "tool_executar_em_docker",
    "tool_exit_loop_se_sucesso",
    "tool_listar_arquivos_coder",
    "tool_verificar_docker",
]

# ===========================================================================
# Instrução do agente
# ===========================================================================

_INSTRUCTION = textwrap.dedent("""\
    # PERFIL
    Você é o **Executor**, responsável por executar o código do coder em Docker
    e decidir se o loop deve continuar ou encerrar.

    # FERRAMENTAS DISPONÍVEIS
    - `tool_verificar_docker()`: verifica conectividade com Docker daemon.
    - `tool_listar_arquivos_coder()`: lista arquivos no workspace do coder.
    - `tool_executar_em_docker()`: builda imagem e roda container + testa rota principal.
    - `tool_exit_loop_se_sucesso()`: encerra o loop. Só funciona se execução foi bem-sucedida.
      (Se a execução falhou, esta ferramenta retornará BLOQUEADO automaticamente.)

    # FLUXO OBRIGATÓRIO
    1. Chame `tool_verificar_docker()`.
       - Se indisponível: reporte falha e encerre SEM chamar tool_exit_loop_se_sucesso.
    2. Chame `tool_listar_arquivos_coder()` para confirmar que há código.
       - Se vazio: reporte falha e encerre SEM chamar tool_exit_loop_se_sucesso.
    3. Chame `tool_executar_em_docker()` para buildar, rodar e testar rota principal.
    4. Analise o resultado:

    ## Se status == "sucesso":
    Chame `tool_exit_loop_se_sucesso()` IMEDIATAMENTE.
    Depois produza um texto confirmando o sucesso, incluindo:
    - A URL de acesso: http://localhost:8000
    - O nome do container (campo `container_name`)
    - "Container mantido em execução para testes manuais."

    ## Se status != "sucesso" (falha_build, falha_runtime, erro):
    NÃO chame tool_exit_loop_se_sucesso (será bloqueado mesmo se tentar).
    Produza um texto DETALHADO com:
    - **Status**: FALHA_BUILD, FALHA_RUNTIME ou ERRO
    - **Resumo**: 1-2 frases sobre o que aconteceu
    - **Erro principal**: o trecho mais relevante dos logs de erro (copie o traceback)
    - **Caminho do relatório**: onde o relatório completo foi salvo

    O coder receberá este texto na próxima iteração e usará as informações
    de erro para corrigir o código. Quanto mais detalhado seu relatório de
    erro, melhor o coder poderá corrigir.

    # REGRAS ABSOLUTAS
    - NÃO modifique código. NÃO faça perguntas. NÃO sugira próximos passos.
    - Em caso de falha, NUNCA tente encerrar o loop — seu relatório será
      entregue ao coder automaticamente na próxima iteração.
""")

# ===========================================================================
# Agente exportado
# ===========================================================================

agent = LlmAgent(
    model=_model,
    name="cr_executor_agent",
    description="Executa código em Docker; exit_loop se sucesso, reporta erro se falha.",
    instruction=_INSTRUCTION,
    output_key="execution_result",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=8192,
    ),
    tools=[
        FunctionTool(tool_executar_em_docker),
        FunctionTool(tool_verificar_docker),
        FunctionTool(tool_listar_arquivos_coder),
        FunctionTool(tool_exit_loop_se_sucesso),
    ],
)
