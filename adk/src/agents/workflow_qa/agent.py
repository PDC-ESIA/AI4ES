"""Workflow de QA / Testes (Time 3).

Orquestrador que conduz o ciclo completo de QA do PDC-AI4SE:
planejamento → geração de testes pytest → autocorreção em caso de falha.
Composto sobre os sub-agentes especialistas do qa_agent.
"""

import json
import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, LongRunningFunctionTool
from google.adk.tools.agent_tool import AgentTool

from src.agents.qa_agent.subagents.integration_tests_agent.agent import agent as integration_tests_agent
from src.agents.qa_agent.subagents.code_fix_agent.agent import agent as code_fix_agent
from src.agents.qa_agent.subagents.unit_test_generator.orchestration import (
    gerar_testes_unitarios,
)
from shared.tools.hitl_tool import aguardar_aprovacao_humana
from shared.tools.pytest_runner import executar_pytest_tool
from shared.tools.doubt_tool import DoubtArtifactGenerator
from src.agents.workflow_qa.tools.planner_wrapper import invocar_planejamento_qa

_DEFAULT_MODEL = "gemini-2.5-flash"


def _emit_qa_manifest(callback_context) -> None:
    """Callback executado ao final do workflow_qa.

    Varre o workspace de testes e emite o Manifesto de Fase `qa` no
    session.state. O conteúdo dos artefatos permanece nos arquivos;
    só os metadados trafegam no state.
    """
    from shared.manifest import (
        ArtifactItem,
        DoubtItem,
        PhaseManifest,
        PhaseStatus,
    )
    from shared.workspace import get_workspace_root

    root = get_workspace_root()
    artifacts: list[ArtifactItem] = []
    test_files = []

    # JSONs de input em tests/inputs/<slug>.json
    inputs_dir = root / "tests" / "inputs"
    if inputs_dir.exists():
        for path in sorted(inputs_dir.iterdir()):
            if path.is_file() and path.suffix == ".json":
                artifacts.append(
                    ArtifactItem(
                        tipo="input",
                        id=path.stem,
                        path=path.relative_to(root).as_posix(),
                    )
                )

    # Código de teste em tests/inputs/<slug>/test_<slug>.py
    tests_dir = root / "tests" / "inputs"
    if tests_dir.exists():
        for slug_dir in sorted(tests_dir.iterdir()):
            if not slug_dir.is_dir():
                continue
            test_file = slug_dir / f"test_{slug_dir.name}.py"
            if test_file.exists():
                test_files.append(test_file)
                artifacts.append(
                    ArtifactItem(
                        tipo="teste",
                        id=slug_dir.name,
                        path=test_file.relative_to(root).as_posix(),
                    )
                )

    reports = []
    for test_file in test_files:
        report_path = test_file.parent / "report.json"
        if not report_path.is_file():
            continue
        try:
            reports.append(json.loads(report_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue

    doubts: list[DoubtItem] = []
    if tests_dir.exists():
        for path in sorted(tests_dir.rglob("Doubt_Artifact_*.md")):
            if path.is_file():
                doubts.append(
                    DoubtItem(
                        id=path.stem,
                        severidade="alta",
                        bloqueante=True,
                        path=path.relative_to(root).as_posix(),
                    )
                )

    def _report_passou(report: dict) -> bool:
        summary = report.get("summary", {})
        return (
            report.get("exitcode") == 0
            and int(summary.get("passed", 0) or 0) > 0
            and int(summary.get("failed", 0) or 0) == 0
            and int(summary.get("skipped", 0) or 0) == 0
            and int(summary.get("error", 0) or 0) == 0
            and int(summary.get("errors", 0) or 0) == 0
        )

    all_reports_passed = (
        bool(test_files)
        and len(reports) == len(test_files)
        and all(_report_passou(report) for report in reports)
    )
    if doubts:
        status = PhaseStatus.BLOCKED
    elif all_reports_passed:
        status = PhaseStatus.OK
    else:
        status = PhaseStatus.PARTIAL

    passed = sum(
        int(report.get("summary", {}).get("passed", 0) or 0)
        for report in reports
    )
    failed = sum(
        int(report.get("summary", {}).get("failed", 0) or 0)
        for report in reports
    )
    skipped = sum(
        int(report.get("summary", {}).get("skipped", 0) or 0)
        for report in reports
    )

    manifest = PhaseManifest(
        phase="qa",
        status=status,
        artifacts=artifacts,
        doubts=doubts,
        summary=(
            f"QA gerou {len(test_files)} teste(s); "
            f"pytest: {passed} passed, {failed} failed, {skipped} skipped; "
            f"dúvidas bloqueantes: {len(doubts)}."
        ),
    )

    state = callback_context.state
    manifests = list(state.get("phase_manifests", []) or [])
    manifests = [
        item for item in manifests
        if not isinstance(item, dict) or item.get("phase") != "qa"
    ]
    manifests.append(manifest.model_dump(mode="json"))

    state["qa_manifest"] = manifest.model_dump(mode="json")
    state["phase_manifests"] = manifests

_INSTRUCTION = """
Você é o pipeline de QA / Testes do Time 3.

PAPEL:
Receber artefatos de requisito (RF, HU, UC, RNF, RN) — opcionalmente
acompanhados de código fonte — e produzir testes unitários pelo perfil da stack
ou testes de integração, corrigindo automaticamente as falhas detectadas.

FLUXO OBRIGATÓRIO:

1. PLANEJAMENTO
   Chame `invocar_planejamento_qa(request=<entrada original>)`.
   Essa função roda o planner com retry automático e GARANTE retorno
   de JSON estruturado (nunca empty). O JSON contém: tipos de teste,
   dependências, pontos de validação humana (HITL) e relatório de
   compliance preliminar.

   → Se `lifecycle.status == "bloqueado"` no JSON retornado:
        Encerre com Doubt_Artifact citando `erro` do JSON.
        Esse caminho só é acionado quando o action_planner não
        conseguiu produzir plano nem com retry — bloqueio legítimo.

   → Se o plano retornar com `hitl_checkpoint.required=true`:
        CHAME OBRIGATORIAMENTE a tool `aguardar_aprovacao_humana`
        passando checkpoint_id, approval_question, allowed_decisions e
        pause_reason extraídos do plano. NÃO emita texto pedindo
        aprovação — a tool faz a pausa real.
        Quando a tool retornar, leia o campo `decision`:
          - "aprovar"           → prossiga para a etapa 2 (geração).
          - "rejeitar"          → encerre com Doubt_Artifact citando
                                  `comments`; não gere testes.
          - "solicitar_ajustes" → encerre devolvendo `comments` ao
                                  solicitante; não gere testes.

2. ROTEAMENTO E EXECUÇÃO
   Execute somente os tipos selecionados no plano:

   TESTE UNITÁRIO (`unit_test_generator`):
   - Chame `gerar_testes_unitarios(artefatos_json=<JSON>)`.
   - A função inspeciona a stack, seleciona um perfil registrado, gera os testes
     e usa o executor fixo do perfil para Python/FastAPI, Node/Express
     (JavaScript e TypeScript), Java/Spring ou Go. O pytest_runner permanece Python.
   - Leia a execução em `detalhes[].resultado_execucao`; não execute novamente
     um resultado já conclusivo.
   - Se `status="bloqueado"`, reporte os bloqueios e não tente outro framework.

   TESTE DE INTEGRAÇÃO (`integration_tests_agent`):
   - Encaminhe os artefatos ao `integration_tests_agent`.
   - O agente seleciona o perfil registrado, gera o arquivo e chama o executor
     próprio de Python, Node/TypeScript, Java ou Go.
   - Leia o envelope normalizado; stdout, stderr e código de saída permanecem
     disponíveis em `resultado_bruto`.
   - Não use o executor pytest legado como fallback de stack.

   Não execute os dois fluxos automaticamente. Só execute ambos quando o plano
   validado contiver explicitamente os dois tipos de teste.
   `arquivos_gerados` e `detalhes[].arquivo_gerado` são as únicas fontes de
   verdade dos paths; nunca invente, resuma ou remapeie caminhos.

3. ANÁLISE DA EXECUÇÃO
   Analise os resultados unitários e/ou de integração selecionados no plano.
   → Se TODOS os testes passaram: vá direto para a entrega final.
   → Se houver falhas: vá para a etapa 4.

4. AUTOCORREÇÃO (Code Fix)
   Encaminhe o relatório de falhas ao code_fix_agent.
   Ele analisa o log, lê o arquivo test_*.py e aplica a correção
   fisicamente com write_qa_test.
   → Passe sempre o path completo retornado em
     `testes_gerados[].arquivo`, não apenas o basename do teste.
   → Exija confirmação `status=aplicado` antes de reexecutar.
   → Nunca execute novamente um arquivo que não foi alterado.
   → O code_fix_agent pode alterar somente código de TESTE, nunca fonte.
   → O code_fix_agent nunca pode criar um teste ausente; ele só corrige um
     `arquivo_gerado` já existente e confirmado pela etapa 2.
   → Nunca peça ao code_fix_agent para alterar sys.path ou apontar para
     workspace_output/coder; os testes usam somente a cópia materializada.
   → Volte para a etapa 3 (re-execução), com no máximo 2 ciclos de
     autocorreção antes de bloquear e gerar Doubt_Artifact.

5. DOUBT ARTIFACT (fallback)
   Em qualquer etapa, se faltar contexto crítico, use a tool
   `DoubtArtifactGenerator.generate` para registrar o bloqueio e
   devolver ao solicitante.

REGRAS:
- Nunca pule a etapa de planejamento (1).
- Nunca tente corrigir código de produção — sua atuação é restrita ao
  código de TESTES.
- Idioma: Português brasileiro.
- Limite a autocorreção a 2 ciclos para evitar loops infinitos.

ENTREGA FINAL AO SOLICITANTE:
- Resumo: {total, sucessos, bloqueados, falhas}.
- Lista de arquivos pytest gerados, com caminhos.
- Relatório de execução do pytest (saída + cobertura).
- Doubt_Artifacts gerados (se houver), com caminho.
- Prompts de correção produzidos pelo code_fix (se houver), com destinatário.
"""

_INSTRUCTION += """

CONTRATO DE CÓDIGO-FONTE PERSISTIDO:
Se a entrada trouxer Manifesto de Fase com artefatos `tipo=source`, preserve
cada `path` e inclua-o em `arquivos_apoio` na chamada a gerar_testes_unitarios.
Paths do manifesto são a fonte canônica. Não declare que o código-fonte está
ausente sem tentar materializar todos esses paths.

O manifesto de Coding NÃO é obrigatório. Mesmo quando ele não estiver na
entrada, chame gerar_testes_unitarios: a inspeção e a camada de I/O descobrem de
forma determinística os fontes persistidos em `workspace_output/coder/src`.
Não solicite alterações em Requirements, Design ou Coding para fazer o handoff.

O retorno de gerar_testes_unitarios preserva `bootstrap_pytest` e
`marcador_pacote`. Use esses campos como fonte de verdade ao relatar a
existência de conftest.py e __init__.py; não afirme que estão ausentes sem
conferir o resultado da tool.
"""

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="qa_pipeline",
    description=(
        "Pipeline completo de QA: planejamento, testes unitários por perfil e "
        "integração multistack, execução e autocorreção. "
        "Compõe action_planner, unit_test_generator, integration_tests_agent e "
        "code_fix sobre as tools do qa_agent."
    ),
    instruction=_INSTRUCTION,
    tools=[
        FunctionTool(invocar_planejamento_qa),
        FunctionTool(gerar_testes_unitarios),
        AgentTool(agent=integration_tests_agent),
        AgentTool(agent=code_fix_agent),
        FunctionTool(executar_pytest_tool),
        FunctionTool(DoubtArtifactGenerator.generate),
        LongRunningFunctionTool(aguardar_aprovacao_humana),
    ],
    after_agent_callback=_emit_qa_manifest,
)
