"""Wrapper rápido e resiliente para o action_planner no qa_pipeline.

Motivação: action_planner via AgentTool retorna ocasionalmente {"result": ""},
travando o qa_pipeline em HITL falso. Este wrapper roda o action_planner em
runner isolado, faz retry programático em caso de empty, e garante que o
caller (qa_pipeline) sempre receba JSON estruturado. Pedidos com escopo único
explícito usam plano determinístico validado, sem chamada ao modelo.
"""

import asyncio
import json
import os
import re
import unicodedata
from typing import Optional

from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types

from src.agents.qa_agent.subagents.action_planner.agent import agent as action_planner_agent
from shared.tools.planner_tools import plan_validator


_EMPTY_THRESHOLD = 8
_DEFAULT_TIMEOUT_SECONDS = 60.0


def _planner_timeout_seconds() -> float:
    try:
        configured = float(
            os.environ.get(
                "AI4ES_QA_PLANNER_TIMEOUT_SECONDS",
                str(_DEFAULT_TIMEOUT_SECONDS),
            )
        )
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS
    return max(10.0, configured)


_FALLBACK_BLOCKED_JSON = (
    '{"tipo_entrada":"indefinido","modo":"indefinido","tools":[],'
    '"casos_de_teste_propostos":[],"lifecycle":{"status":"bloqueado",'
    '"execution_allowed":false,"next_step":"aguardar_resolucao_humana"},'
    '"erro":"action_planner não respondeu após 2 tentativas — falha de modelo"}'
)

_RETRY_PROMPT_SUFFIX = (
    "\n\nATENÇÃO: sua resposta anterior foi vazia ou inválida. "
    "Responda OBRIGATORIAMENTE com JSON válido seguindo o schema do PROTOCOLO ANTI-EMPTY. "
    "Se você não conseguir planejar (input incompleto, ambíguo, contraditório), "
    "devolva o JSON de bloqueio: "
    '{"tipo_entrada":"indefinido","modo":"indefinido","tools":[],'
    '"casos_de_teste_propostos":[],"lifecycle":{"status":"bloqueado",'
    '"execution_allowed":false,"next_step":"aguardar_resolucao_humana"},'
    '"erro":"<motivo curto>"}'
)


def _is_empty(text: Optional[str]) -> bool:
    """True quando o texto é vazio, None, só whitespace ou só backticks.

    Heurística: <_EMPTY_THRESHOLD chars úteis = empty.
    """
    if text is None:
        return True
    stripped = text.strip().strip("`").strip()
    return len(stripped) < _EMPTY_THRESHOLD


def _needs_retry(text: Optional[str]) -> bool:
    """True para resposta vazia ou marcador de falha operacional transitória."""
    if _is_empty(text):
        return True
    return text.lstrip().casefold().startswith("error:")


def _normalizar(texto: str) -> str:
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto).casefold()
        if not unicodedata.combining(caractere)
    )


def _plano_rapido(request: str) -> Optional[str]:
    """Gera plano validado quando o usuário delimitou exatamente um nível."""
    normalizado = _normalizar(request)
    candidatos: list[tuple[str, str]] = []
    prefixo = r"(?:somente|apenas|exclusiv\w*|limitad\w*)[^.!?\n]{0,100}"
    if re.search(prefixo + r"(?:e2e|playwright)", normalizado):
        candidatos.append(("e2e", "e2e_test_generator"))
    if re.search(prefixo + r"integracao", normalizado):
        candidatos.append(("integração", "integration_tests_agent"))
    if re.search(prefixo + r"(?:unitari\w*|unit test)", normalizado):
        candidatos.append(("unitário", "unit_test_generator"))
    if len(candidatos) != 1:
        return None

    nivel, tool = candidatos[0]
    linguagem = "desconhecida"
    for marcador, nome in (
        ("typescript", "typescript"),
        ("javascript", "javascript"),
        ("python", "python"),
        ("java", "java"),
        ("golang", "go"),
    ):
        if marcador in normalizado:
            linguagem = nome
            break

    plano = {
        "tipo_entrada": "requisito",
        "modo": "requisito",
        "tools": [tool],
        "casos_de_teste_propostos": [
            f"Executar somente teste {nivel} conforme os critérios da entrada."
        ],
        "lifecycle": {
            "status": "planejado_para_execucao",
            "execution_allowed": True,
            "next_step": "executar_plano",
        },
        "hitl_checkpoint": {
            "required": False,
            "checkpoint_id": None,
            "pause_reason": None,
            "approval_question": None,
            "allowed_decisions": [],
        },
        "risk_assessment": {
            "nivel": "baixo",
            "motivos": ["Teste local, reversível e com escopo único explícito."],
            "acoes_reversiveis": True,
            "efeito_externo": False,
        },
        "autonomy_decision": {
            "mode": "autonomous",
            "reason": "O nível de teste foi delimitado explicitamente.",
            "less_prompt_more_action": True,
        },
        "analise_inicial": {
            "linguagem_suspeita": linguagem,
            "funcao_suspeita_do_codigo": None,
            "nivel_de_confianca": 1.0 if linguagem != "desconhecida" else 0.5,
        },
        "analise_progressiva": [
            {
                "observacao": f"A entrada solicita somente teste {nivel}.",
                "hipotese": "O perfil pode ser detectado no código persistido.",
                "validacao_planejada": "Inspecionar, gerar, executar e normalizar.",
            }
        ],
        "resumo_do_requisito": request,
        "criterios_verificaveis": [
            "Perfil compatível detectado.",
            "Teste gerado e executado.",
            "Resultado normalizado retornado.",
        ],
        "objetivo_qa": f"Executar somente o fluxo {nivel} solicitado.",
        "estrategia": [
            "Inspecionar o projeto persistido.",
            f"Gerar e executar teste {nivel} pelo perfil detectado.",
            "Retornar resultado normalizado.",
        ],
        "checklist_inicial": [
            {"id": "CHK-01", "descricao": "Detectar perfil.", "status": "pendente"},
            {"id": "CHK-02", "descricao": "Executar testes.", "status": "pendente"},
            {"id": "CHK-03", "descricao": "Normalizar resultado.", "status": "pendente"},
        ],
        "handoff_context": {
            "objetivo": f"Executar somente teste {nivel}.",
            "contexto_compacto": "Escopo único explícito; código já persistido.",
            "entrada_original": request,
            "artefatos_relevantes": ["workspace_output/coder/src"],
            "decisoes_tomadas": [f"Selecionar somente {tool}."],
            "riscos_e_duvidas": [],
            "evidencias_necessarias": ["Arquivo gerado", "Resultado normalizado"],
        },
        "relatorio_conformidade_esperado": {
            "comparar_planejado_vs_executado": True,
            "incluir_evidencias": True,
            "incluir_divergencias": True,
            "status_possiveis": [
                "conforme",
                "parcialmente_conforme",
                "nao_conforme",
            ],
        },
        "doubt": None,
    }
    validacao = plan_validator(json.dumps(plano, ensure_ascii=False))
    if not validacao.get("valid"):
        return None
    return json.dumps(validacao["validated_plan"], ensure_ascii=False)


async def _invoke_once(request: str, user_id: str = "qa-pipeline") -> str:
    """Roda action_planner uma vez em runner isolado, retorna last_text.

    Em caso de exceção do Runner, devolve string 'ERROR: <msg>' em vez de
    propagar — para que invocar_planejamento_qa possa decidir fallback.
    """
    runner = None
    try:
        runner = Runner(
            app_name=action_planner_agent.name,
            agent=action_planner_agent,
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        session = await runner.session_service.create_session(
            app_name=action_planner_agent.name, user_id=user_id, state={},
        )
        content = types.Content(
            role="user", parts=[types.Part.from_text(text=request)],
        )
        async def _coletar_resposta() -> str:
            last_text = ""
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=content,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            last_text = part.text
            return last_text

        return await asyncio.wait_for(
            _coletar_resposta(), timeout=_planner_timeout_seconds()
        )
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"
    finally:
        if runner is not None:
            try:
                await runner.close()
            except Exception:
                pass


async def invocar_planejamento_qa(request: str) -> str:
    """Invoca action_planner com retry programático.

    Garantia: sempre devolve string não-vazia com JSON estruturado.
    Caller (qa_pipeline) pode parsear sem se preocupar com empty.

    Args:
        request: texto do request original (requisitos + código se houver).

    Returns:
        JSON string com plano (válido) ou _FALLBACK_BLOCKED_JSON quando
        action_planner falhar duas vezes seguidas.
    """
    plano_rapido = _plano_rapido(request)
    if plano_rapido is not None:
        return plano_rapido

    first = await _invoke_once(request)
    if not _needs_retry(first):
        return first

    second = await _invoke_once(request + _RETRY_PROMPT_SUFFIX)
    if not _needs_retry(second):
        return second

    return _FALLBACK_BLOCKED_JSON
