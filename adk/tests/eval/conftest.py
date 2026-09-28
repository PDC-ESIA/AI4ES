"""Mecânica da avaliação de agentes com o `AgentEvaluator` do ADK.

Opt-in: sem `AI4ES_EVAL=1`, tudo daqui é pulado, inclusive num `uv run pytest` sem
argumentos. Com ela, o módulo prepara o ambiente no import, numa ordem que importa
(comentários em `_preparar_ambiente`), e imprime o custo da rodada ao final.

    AI4ES_EVAL=1 uv run --group eval pytest tests/eval -q
"""

from __future__ import annotations

import importlib
import os
import shutil
import sys
from pathlib import Path

import pytest

_AQUI = Path(__file__).resolve().parent

# `tests` é namespace package, e o hook de asserções do pytest o sombreia dentro dos
# módulos de teste: importar `metrics` aqui o deixa em `sys.modules` antes da coleta.
_RAIZ_ADK = _AQUI.parents[1]
if str(_RAIZ_ADK) not in sys.path:
    sys.path.insert(0, str(_RAIZ_ADK))

from tests.eval import metrics  # noqa: E402  -- depende do sys.path acima

#: Ligado só com AI4ES_EVAL=1. Ver `pytest_collection_modifyitems`.
LIGADO = os.environ.get("AI4ES_EVAL") == "1"

#: Workspace isolado da avaliação. Coberto pelo `.gitignore` (`workspace_output/`).
WORKSPACE = Path(
    os.environ.get("AI4ES_EVAL_WORKSPACE") or (_AQUI / "workspace_output")
).resolve()

#: Obrigatórias para qualquer métrica (a cadeia de import do registry de métricas do
#: ADK passa por elas). Vêm do grupo `eval` do pyproject.toml.
_DEPENDENCIAS = ("pandas", "rouge_score")

_COMANDO = "AI4ES_EVAL=1 uv run --group eval pytest tests/eval -q"

#: `fixtures/` e `workspace_output/` guardam o projeto fictício que os agentes analisam,
#: com testes próprios; não são testes desta suíte.
collect_ignore = ["fixtures", "workspace_output"]


def dependencias_ausentes() -> list[str]:
    """Extras do ADK que faltam, detectados antes de a avaliação começar."""
    ausentes = []
    for modulo in _DEPENDENCIAS:
        try:
            importlib.import_module(modulo)
        except ImportError:
            ausentes.append(modulo)
    return ausentes


_AUSENTES = dependencias_ausentes()
_METRICAS_REGISTRADAS: list[str] = []
_ERRO_DE_SETUP: str | None = None


def _preparar_ambiente() -> None:
    """Prepara o ambiente da avaliação. Chamado só quando LIGADO."""
    global _METRICAS_REGISTRADAS, _ERRO_DE_SETUP

    # (1) Antes de qualquer import de agente: tools resolvem o workspace no import.
    os.environ["WORKSPACE_OUTPUT_DIR"] = str(WORKSPACE)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    # O marker é o que autoriza `init_workspace()` a limpar este diretório.
    (WORKSPACE / ".ai4se_workspace").write_text(
        "Workspace da PoC de avaliacao (tests/eval). Recriado a cada caso.\n",
        encoding="utf-8",
    )

    # (2) Como o uvicorn faz: carrega o .env e resolve os modelos na mesma ordem.
    importlib.import_module("app.main")

    # (3) Registra as métricas próprias no ADK.
    _METRICAS_REGISTRADAS = metrics.registrar_metricas_ai4es()

    # (4) Guarda: o reviewer congela o workspace no import; conferir onde caiu.
    review_tools = importlib.import_module("shared.tools.coding_tools.review_tools")
    coder_ws = Path(review_tools._CODER_WS).resolve()
    if coder_ws != WORKSPACE and WORKSPACE not in coder_ws.parents:
        _ERRO_DE_SETUP = (
            "O binding do cr_review_analyzer aponta para fora do workspace da "
            f"avaliação.\n  esperado dentro de: {WORKSPACE}\n  obtido: {coder_ws}\n\n"
            "Causa: review_tools.py resolve _CODER_WS em tempo de IMPORT, então "
            "algum outro módulo importou o reviewer antes deste conftest rodar. "
            "Rode a avaliação sozinha (`pytest tests/eval`), não junto de tests/unit."
        )

    # (5) Contador de custo: o AgentEvaluator não reporta chamadas, tokens nem tempo.
    _instalar_contador_de_custo()


#: Uma entrada por chamada de LLM: {modelo, segundos, prompt, completion}.
CHAMADAS_LLM: list[dict] = []


def _instalar_contador_de_custo() -> None:
    """Registra um callback do LiteLLM que contabiliza cada chamada de LLM."""
    import litellm
    from litellm.integrations.custom_logger import CustomLogger

    class _Contador(CustomLogger):
        def _registrar(self, kwargs, response_obj, start_time, end_time):
            registro = {
                "modelo": kwargs.get("model"),
                "segundos": None,
                "prompt": 0,
                "completion": 0,
            }
            try:
                registro["segundos"] = round((end_time - start_time).total_seconds(), 2)
            except Exception:
                pass
            try:
                uso = response_obj.usage
                registro["prompt"] = getattr(uso, "prompt_tokens", 0) or 0
                registro["completion"] = getattr(uso, "completion_tokens", 0) or 0
            except Exception:
                pass
            CHAMADAS_LLM.append(registro)

        def log_success_event(self, kwargs, response_obj, start_time, end_time):
            self._registrar(kwargs, response_obj, start_time, end_time)

        async def async_log_success_event(
            self, kwargs, response_obj, start_time, end_time
        ):
            self._registrar(kwargs, response_obj, start_time, end_time)

    litellm.callbacks = [*(litellm.callbacks or []), _Contador()]


if LIGADO and not _AUSENTES:
    _preparar_ambiente()


# ---------------------------------------------------------------------------
# Hooks do pytest
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "eval: avaliação com LLM real via AgentEvaluator do ADK (opt-in, AI4ES_EVAL=1)",
    )
    config.addinivalue_line(
        "markers",
        "eval_juiz: avaliação com métrica de juiz LLM (opt-in adicional, AI4ES_EVAL_JUIZ=1)",
    )


def pytest_collection_modifyitems(config, items):
    """Pula tudo deste diretório quando a avaliação não foi pedida.

    O hook é global, então filtra por caminho — não pode tocar em tests/unit.
    """
    juiz_ligado = os.environ.get("AI4ES_EVAL_JUIZ") == "1"

    if not LIGADO:
        motivo = pytest.mark.skip(
            reason=f"avaliação desligada; gasta LLM real. Para rodar: {_COMANDO}"
        )
    elif _AUSENTES:
        motivo = pytest.mark.skip(
            reason=(
                f"faltam os extras do ADK eval: {', '.join(_AUSENTES)}. "
                "São obrigatórios para qualquer métrica e ficam no grupo `eval` do "
                f"pyproject.toml. Rode: {_COMANDO}"
            )
        )
    else:
        motivo = None

    de_fora = 0
    for item in items:
        try:
            dentro = _AQUI in Path(str(item.fspath)).resolve().parents
        except OSError, ValueError:
            dentro = False
        if not dentro:
            de_fora += 1
            continue
        if motivo is not None:
            item.add_marker(motivo)
        elif "eval_juiz" in item.keywords and not juiz_ligado:
            item.add_marker(
                pytest.mark.skip(
                    reason="métrica de juiz é opt-in adicional: AI4ES_EVAL_JUIZ=1"
                )
            )

    if LIGADO and de_fora:
        config.issue_config_time_warning(
            UserWarning(
                f"AI4ES_EVAL=1 com {de_fora} teste(s) fora de tests/eval na mesma "
                "sessão. WORKSPACE_OUTPUT_DIR foi redirecionado para o workspace da "
                "avaliação e pode afetá-los. Rode `pytest tests/eval` sozinho."
            ),
            stacklevel=2,
        )


@pytest.fixture(scope="session", autouse=True)
def _validar_setup():
    """Falha alto e cedo se a guarda de coerência do import pegou algo."""
    if _ERRO_DE_SETUP:
        pytest.fail(_ERRO_DE_SETUP, pytrace=False)


def pytest_terminal_summary(terminalreporter):
    """Resumo de custo da rodada (chamadas, tokens, tempo), que o ADK não reporta."""
    if not LIGADO or not CHAMADAS_LLM:
        return

    entrada = sum(c["prompt"] for c in CHAMADAS_LLM)
    saida = sum(c["completion"] for c in CHAMADAS_LLM)
    segundos = sum(c["segundos"] or 0 for c in CHAMADAS_LLM)
    modelos = sorted({c["modelo"] for c in CHAMADAS_LLM if c["modelo"]})

    terminalreporter.write_sep("=", "custo da avaliação")
    terminalreporter.write_line(f"chamadas de LLM : {len(CHAMADAS_LLM)}")
    terminalreporter.write_line(
        f"tokens          : prompt={entrada}  completion={saida}  total={entrada + saida}"
    )
    terminalreporter.write_line(f"tempo em LLM    : {segundos:.1f}s")
    terminalreporter.write_line(f"modelo(s)       : {', '.join(modelos)}")
    terminalreporter.write_line(
        f"num_runs        : {os.environ.get('AI4ES_EVAL_NUM_RUNS', '2')}"
        "   (limiar 1.0 exige conformidade em todas)"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_semeado():
    """Recria o workspace da avaliação com `init_workspace()` e copia uma fixture."""
    from shared.workspace import init_workspace

    def _semear(nome_fixture: str) -> Path:
        origem = _AQUI / "fixtures" / nome_fixture
        if not origem.is_dir():
            raise FileNotFoundError(f"fixture inexistente: {origem}")
        raiz = init_workspace()
        shutil.copytree(origem, raiz, dirs_exist_ok=True)
        return raiz

    return _semear


@pytest.fixture
def evalset(tmp_path):
    """Copia um eval set para `tmp_path`, resolvendo os placeholders.

    `{{WORKSPACE}}` vira o workspace da avaliação. `{{JUDGE_MODEL}}` vira
    `AI4ES_EVAL_JUDGE_MODEL` ou, na falta, `ADK_LLM_MODEL`; sem nenhum dos dois, falha
    aqui, em vez de o ADK cair no juiz default, que exige credencial Google. A pasta vai
    inteira porque o ADK procura o `test_config.json` ao lado do arquivo de casos.
    """

    def _preparar(nome: str) -> str:
        origem = _AQUI / "evalsets" / nome
        if not origem.is_dir():
            raise FileNotFoundError(f"eval set inexistente: {origem}")

        destino = tmp_path / nome
        shutil.copytree(origem, destino)

        for arquivo in destino.glob("*.json"):
            texto = arquivo.read_text(encoding="utf-8")
            texto = texto.replace("{{WORKSPACE}}", WORKSPACE.as_posix())
            if "{{JUDGE_MODEL}}" in texto:
                juiz = os.environ.get("AI4ES_EVAL_JUDGE_MODEL") or os.environ.get(
                    "ADK_LLM_MODEL"
                )
                if not juiz:
                    raise AssertionError(
                        f"{arquivo.name} usa {{{{JUDGE_MODEL}}}} mas nem "
                        "AI4ES_EVAL_JUDGE_MODEL nem ADK_LLM_MODEL estão definidas."
                    )
                texto = texto.replace("{{JUDGE_MODEL}}", juiz)
            arquivo.write_text(texto, encoding="utf-8")

        casos = sorted(destino.glob("*.test.json"))
        if len(casos) != 1:
            raise AssertionError(
                f"esperado exatamente 1 arquivo *.test.json em {origem}, achei {len(casos)}"
            )
        return str(casos[0])

    return _preparar


@pytest.fixture
def rodar_eval():
    """Chama `AgentEvaluator.evaluate` com os defaults da suíte."""
    from google.adk.evaluation.agent_evaluator import AgentEvaluator

    async def _rodar(
        caminho_evalset: str,
        agent_module: str,
        agent_name: str | None = None,
        num_runs: int | None = None,
    ) -> None:
        await AgentEvaluator.evaluate(
            agent_module=agent_module,
            eval_dataset_file_path_or_dir=caminho_evalset,
            num_runs=num_runs or int(os.environ.get("AI4ES_EVAL_NUM_RUNS", "2")),
            agent_name=agent_name,
            print_detailed_results=os.environ.get("AI4ES_EVAL_DETALHE") == "1",
        )

    return _rodar
