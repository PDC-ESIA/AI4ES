"""Reviewer dedicado ao workflow coding_review.

Instância ajustada do reviewer original (src/agents/reviewer/):
- Analyzer: lê arquivos de coder/src/ (não diff git), produz análise markdown.
- Análise estática pré-LLM via before_agent_callback (Ruff + Bandit).
- Persistência via after_agent_callback Python puro — sem LLM no passo de escrita.
  Isso elimina o risco de "modo narrador" (LLM descreve a chamada em vez de executá-la).
- Evita conflito de parent com o sdlc_pipeline (instância dedicada).

Variáveis de ambiente:
    REVIEWER_STATIC_ANALYSIS: "0" desabilita análise estática pré-LLM (padrão: habilitado).
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from shared.agent_factory import _bind_tool_to_workspace
from shared.review import run_capabilities
from shared.workspace import get_agent_workspace, get_workspace_root
from shared.tools import tool_ler_arquivo, tool_salvar_relatorio

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
else:
    CallbackContext = Any  # type: ignore[misc,assignment]

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)
_STATIC_ANALYSIS_ENABLED = os.environ.get("REVIEWER_STATIC_ANALYSIS", "1") != "0"
_MAX_FINDINGS = 30

_WORKSPACE_ROOT = str(get_workspace_root())
_CODER_WS = str(get_agent_workspace("cr_coder"))
_REVIEW_WS = str(get_agent_workspace("cr_reviewer"))


def _bind(tool, agent_ws):
    return _bind_tool_to_workspace(tool, agent_ws, _WORKSPACE_ROOT)


def _discover_coder_files() -> str:
    """Lista arquivos no _CODER_WS (relativo), formato bullet.

    Executado no momento da invocação do agente (via InstructionProvider).
    Quando o coder ainda não rodou, retorna marker informativo.
    """
    coder_dir = Path(_CODER_WS)
    if not coder_dir.exists():
        return "- (nenhum arquivo ainda — coder será executado antes de você)"
    files = sorted(
        p.relative_to(coder_dir).as_posix()
        for p in coder_dir.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    if not files:
        return "- (workspace vazio)"
    return "\n".join(f"- {f}" for f in files)


# ---------------------------------------------------------------------------
# Analyzer — prompt materializado (anteriormente derivado de
# src/agents/reviewer/prompt.py com 6 .replace() para adaptar ao workspace).
# ---------------------------------------------------------------------------

_ANALYZER_BASE = """\

# PAPEL E PERFIL
Você é um Engenheiro de Software Sênior especializado em **Verificação de Código**.
Sua função é analisar o código produzido pelo agente anterior e decidir se ele está
tecnicamente correto e íntegro para prosseguir no pipeline.

Você NÃO faz validação de requisitos (se o requisito faz sentido). Você faz
**verificação**: o código foi construído corretamente?

# FLUXO DE VERIFICAÇÃO (4 CAMADAS — executar em ordem)

## Camada 1: COMPLETUDE
Objetivo: Todos os artefatos esperados foram entregues?
1. Leia os arquivos criados pelo coder no workspace (listados abaixo em ARQUIVOS A REVISAR).
2. Compare com a DoD (Definition of Done) implícita no requisito recebido do
   agente anterior (state["requirements"] ou state["tasks"]).
3. Verifique: arquivos esperados foram criados? testes foram entregues junto
   com a implementação? documentação foi atualizada?
4. Registre issues de completude (ex: "Arquivo de testes não foi criado", layer="completude").

## Camada 2: ARQUITETURA
Objetivo: A estrutura do código segue boas práticas?
1. Examine os arquivos listados em ARQUIVOS A REVISAR.
2. Verifique:
   - Responsabilidade única (SRP) — cada módulo/classe tem um propósito claro?
   - Acoplamento — dependências circulares? Imports desnecessários?
   - Separação de concerns — lógica de negócio misturada com I/O ou framework?
3. Registre issues de arquitetura (layer="arquitetura").

## Camada 3: CORRETUDE
Objetivo: O código funciona corretamente?
1. Examine o corpo das funções de lógica core nos arquivos.
2. Verifique:
   - Erros de lógica, off-by-one, loops infinitos.
   - Exceções não tratadas ou silenciadas.
   - Falhas de segurança (injeção, path traversal, dados sensíveis expostos).
   - Edge cases não cobertos.
3. Registre issues de corretude (layer="corretude").

## Camada 4: TESTES
Objetivo: Os testes existem e cobrem os cenários relevantes?
1. Verifique se arquivos de teste foram criados no workspace.
2. Examine o conteúdo dos testes.
3. Verifique:
   - Cenários críticos (happy path + edge cases) estão cobertos?
   - Testes são independentes e determinísticos?
   - Assertions são significativas (não apenas "assert True")?
4. Registre issues de testes (layer="testes").

# REGRAS DE DECISÃO
- Se houver **qualquer issue `critical`** → status = "BLOQUEADO"
- Se houver apenas `warning` ou `info` → status = "APROVADO" (com ressalvas documentadas)
- Sem issues → status = "APROVADO"

# THINKING (use antes de emitir o veredito)
<thinking>
- Completude: Os artefatos esperados foram entregues? Quais faltam?
- Arquitetura: A estrutura respeita SOLID? Há acoplamento indevido?
- Corretude: Há bugs, edge cases ou falhas de segurança?
- Testes: Existem? Cobrem os cenários críticos?
- Veredito: APROVADO ou BLOQUEADO?
</thinking>

# SAÍDA
Sua responsabilidade é PRODUZIR A ANÁLISE em markdown — a persistência em disco
é feita automaticamente pelo pipeline após sua resposta.

Produza markdown com seções:
- "## Status: APROVADO" ou "## Status: BLOQUEADO"
- "## Issues" (lista por severidade com arquivo/camada/descrição)
- "## Resumo" (1 parágrafo)

NÃO produza JSON literal.
"""

# Template final: injeta análise estática, workspace e lista de arquivos em runtime
_ANALYZER_INSTRUCTION_TEMPLATE = (
    _ANALYZER_BASE + "\n\n"
    "# ANÁLISE ESTÁTICA (pré-LLM)\n"
    "Os seguintes problemas foram identificados por ferramentas determinísticas\n"
    "(Ruff e Bandit) antes desta análise. Use-os como ponto de partida e\n"
    "complemente com sua revisão das 4 camadas:\n\n"
    "__STATIC_FINDINGS__\n\n"
    "# WORKSPACE\n"
    "Os arquivos a revisar estão em `__CODER_WS__/`.\n"
    "Use caminhos RELATIVOS — tool_ler_arquivo resolve automaticamente.\n\n"
    "# ARQUIVOS A REVISAR\n"
    "__FILES__\n"
)


def _format_findings_block(findings) -> str:
    """Formata lista de Finding em bloco legível para o prompt do LLM."""
    if not findings:
        return "Nenhum problema identificado pelas ferramentas de análise estática."
    lines = []
    for f in findings:
        loc = f"{f.arquivo}:{f.linha}" if f.linha else f.arquivo
        lines.append(f"[{f.severidade.upper()}] {f.origem}/{f.regra} — {loc}\n  {f.mensagem}")
    return "\n".join(lines)


def _analyzer_instruction_provider(ctx) -> str:
    """InstructionProvider: injeta findings estáticos e lista de arquivos em runtime."""
    static_block = ""
    if hasattr(ctx, "state"):
        static_block = ctx.state.get("static_findings_block", "")
    return (
        _ANALYZER_INSTRUCTION_TEMPLATE
        .replace("__STATIC_FINDINGS__", static_block or "Análise estática não disponível.")
        .replace("__CODER_WS__", _CODER_WS)
        .replace("__FILES__", _discover_coder_files())
    )


def _inject_static_findings(callback_context: CallbackContext) -> None:
    """Roda análise estática no workspace do coder antes do LLM analisar.

    Injeta o bloco de findings em state["static_findings_block"] para que
    _analyzer_instruction_provider o inclua no prompt em runtime.
    Retorna None para não interromper a execução do agente.
    """
    if not _STATIC_ANALYSIS_ENABLED:
        return None
    coder_path = Path(_CODER_WS)
    if not coder_path.exists():
        callback_context.state["static_findings_block"] = (
            "Workspace do coder não encontrado — análise estática ignorada."
        )
        return None
    findings = run_capabilities(coder_path)
    capped = findings[:_MAX_FINDINGS]
    callback_context.state["static_findings_block"] = _format_findings_block(capped)
    return None


def _persist_review(callback_context: CallbackContext) -> None:
    """Persiste o relatório de revisão no disco — zero LLM no passo de escrita.

    Executado pelo runtime do ADK após _analyzer terminar.
    Lê review_analysis do callback_context.state e chama tool_salvar_relatorio
    diretamente em Python, eliminando o risco de modo narrador.

    Raises:
        RuntimeError: se tool_salvar_relatorio retornar sucesso=False
            (cobre tanto falha de I/O quanto parâmetros inválidos).
    """
    analysis_raw = callback_context.state.get("review_analysis")
    if analysis_raw is None:
        return
    analysis = str(analysis_raw)
    if not analysis.strip():
        return
    result = tool_salvar_relatorio(
        conteudo=analysis,
        nome_arquivo="verificacao_revisao.md",
        base_dir=_REVIEW_WS,
    )
    if not result.get("sucesso"):
        raise RuntimeError(
            "Falha ao persistir relatório de revisão em "
            f"'{result.get('caminho') or 'verificacao_revisao.md'}': {result.get('erro')}"
        )


_analyzer = LlmAgent(
    model=_model,
    name="cr_review_analyzer",
    description="Revisão de código: lê arquivos do coder, produz análise markdown e persiste via callback.",
    instruction=_analyzer_instruction_provider,
    output_key="review_analysis",
    tools=[
        _bind(FunctionTool(tool_ler_arquivo), _CODER_WS),
    ],
)
_analyzer.before_agent_callback = _inject_static_findings
_analyzer.after_agent_callback = _persist_review

# agent é exportado como LlmAgent (not SequentialAgent) — a persistência acontece
# via after_agent_callback, sem necessidade de um segundo agente no pipeline.
agent = _analyzer
