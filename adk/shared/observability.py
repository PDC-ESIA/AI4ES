"""Observabilidade: liga o logging/tracing NATIVO do ADK.

Este módulo é o ponto central de configuração de observabilidade — que antes
inexistia. Em vez de construir infra própria, ele ativa o que o google-adk já
traz embutido:

- ``setup_adk_logger`` (google.adk.cli.utils.logs): configura ``basicConfig``
  com timestamp + nível + ``file:lineno`` e controla o namespace ``google_adk``.
- Plugins nativos (google.adk.plugins): ``LoggingPlugin`` (loga no console cada
  ponto crítico da invocação: mensagem do usuário, início/fim de agente,
  request/response de LLM, tool calls com args/resultados e erros) e
  ``DebugLoggingPlugin`` (mesma informação, estruturada em arquivo YAML).

Como ``orchestrator/agent.py`` repassa ``plugins=ctx.plugin_manager.plugins``
para os Runners internos, um plugin registrado no nível do app cascateia
automaticamente para os 4 sub-pipelines (requirements → design → coding_review
→ qa) e todos os sub-agentes aninhados.

Knobs (via ambiente):
    LOG_LEVEL          Nível do logger raiz/``google_adk`` (default: INFO).
    ADK_LOG_PLUGIN     off | console | file (default: console).
    ADK_DEBUG_LOG_PATH Caminho do YAML quando ADK_LOG_PLUGIN=file
                       (default: <raiz do repo>/logs/adk_debug.yaml — fora de
                       workspace_output/ de propósito, ver _debug_log_path).
    LANGFUSE_PUBLIC_KEY Opt-in para tracing externo via Langfuse +
                       OpenInference — ver ``setup_langfuse()``. Ausente por
                       padrão: sem essa variável, nenhuma dependência de
                       Langfuse/OpenTelemetry é sequer importada.

RISCO RESIDUAL (não coberto por este módulo hoje): ``LoggingPlugin`` e
``DebugLoggingPlugin`` — os dois plugins nativos acima — NÃO passam pelo
módulo ``logging`` do Python para o conteúdo que capturam.
``LoggingPlugin._log()`` escreve com ``print()`` direto; ``DebugLoggingPlugin``
grava o YAML via ``os.fdopen()`` + ``yaml.dump()`` direto no arquivo (ambos em
``google/adk/plugins/`` do pacote instalado). Como ``_FiltroDeSegredos``
(abaixo) só intercepta ``LogRecord`` entregues a um ``Handler`` — e nenhum dos
dois plugins gera um — nenhum dos dois é coberto por ele: prompt e resposta
completos de todo agente vão para o stdout (modo console) ou para o arquivo
(modo file) com apenas a redação estruturada nativa do ADK (por nome de
campo/chave — ``api_key``, ``token``, ``secret``, blocos de chave privada
armored — ver ``DebugLoggingPlugin`` instalado), não uma varredura de texto
livre como ``redigir_segredos`` faz. Uma credencial embutida em prosa (não
sob um nome de campo reconhecido) chega inteira em ambos os destinos. Cobrir
isso exigiria uma subclasse/wrapper de ``LoggingPlugin``/``DebugLoggingPlugin``
que redigisse antes do ``print``/``yaml.dump`` — não implementado ainda,
registrado aqui como risco conhecido.
"""

import logging
import os
import re
from pathlib import Path

from google.adk.cli.utils.logs import setup_adk_logger
from google.adk.plugins import DebugLoggingPlugin

from shared.security import redigir_segredos

logger = logging.getLogger(__name__)

# Raiz do repositório ADK (shared/observability.py -> shared/ -> adk/).
_RAIZ_ADK = Path(__file__).resolve().parents[1]

# Default fora de workspace_output/: esse diretório é lido por tools de
# agente (ex.: inspecionar_projeto_e2e do QA, que varre um `workspace_projeto`
# dentro do workspace gerenciado) — um log com prompt/resposta completos de
# TODOS os agentes não pode estar num diretório que qualquer agente pode
# pedir para ler. `_arquivos_do_workspace` também exclui este arquivo
# explicitamente como defesa extra (ver
# e2e_test_generator/tools/inspecionar_projeto_e2e.py:_caminho_debug_log_excluido),
# mas a primeira linha de defesa é simplesmente não estar ali.
_DEBUG_LOG_PADRAO = _RAIZ_ADK / "logs" / "adk_debug.yaml"


def _debug_log_path() -> str:
    """Resolve ADK_DEBUG_LOG_PATH, criando o diretório do default se preciso.

    Um valor customizado de ADK_DEBUG_LOG_PATH é usado tal como está (mesmo
    comportamento de sempre — string relativa resolvida pelo próprio
    DebugLoggingPlugin/yaml contra o cwd). Só o DEFAULT muda de local.
    """
    customizado = os.environ.get("ADK_DEBUG_LOG_PATH")
    if customizado:
        return customizado
    _DEBUG_LOG_PADRAO.parent.mkdir(parents=True, exist_ok=True)
    return str(_DEBUG_LOG_PADRAO)


# Instância pré-configurada do plugin de arquivo. Referenciável por nome
# qualificado em `extra_plugins` — o loader do ADK aceita instâncias de
# BasePlugin diretamente (não só classes), permitindo injetar output_path.
debug_logging_plugin = DebugLoggingPlugin(output_path=_debug_log_path())


def _resolve_level(default: int = logging.INFO) -> int:
    """Traduz LOG_LEVEL (nome ou número) para o int do módulo logging."""
    raw = os.environ.get("LOG_LEVEL")
    if not raw:
        return default
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    return getattr(logging, raw.upper(), default)


class _FiltroDeSegredos(logging.Filter):
    """Aplica ``redigir_segredos`` a toda mensagem que passe por um handler
    padrão do módulo ``logging`` (ex.: ``logger.warning(...)`` deste projeto,
    em ``shared/`` e ``src/agents/...``).

    IMPORTANTE — o que este filtro NÃO protege: nem ``LoggingPlugin`` nem
    ``DebugLoggingPlugin`` (google-adk nativo) emitem os prompts/respostas/
    tool calls que capturam como ``LogRecord``, então nenhum ``logging.Filter``
    consegue interceptá-los, não importa onde seja registrado:
    - ``LoggingPlugin._log()`` chama ``print()`` direto (ver
      ``google/adk/plugins/logging_plugin.py``), nunca ``logging``.
    - ``DebugLoggingPlugin`` escreve o YAML via ``os.fdopen()`` +
      ``yaml.dump()`` direto no arquivo (ver
      ``google/adk/plugins/debug_logging_plugin.py``), também fora do
      módulo ``logging``.
    ``DebugLoggingPlugin`` já tem redação própria para credenciais em campos
    estruturados conhecidos (por nome de chave — ``api_key``, ``token``,
    ``secret``, blocos de chave privada armored, etc.), mas por design não
    varre o texto livre de prompt/resposta em busca de segredo embutido —
    a própria docstring da classe instalada admite isso ("the file still
    holds whole prompts and responses"). É exatamente essa lacuna que
    ``redigir_segredos`` cobre, mas só alcança o que passa por ``logging``.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redigir_segredos(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    chave: redigir_segredos(valor) if isinstance(valor, str) else valor
                    for chave, valor in record.args.items()
                }
            else:
                record.args = tuple(
                    redigir_segredos(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


def setup_logging() -> None:
    """Configura o logging nativo do ADK a partir de LOG_LEVEL.

    Substitui o antigo ``logger.setLevel`` local de app/main.py (que não
    instalava handler). Idempotente o suficiente para ser chamado no boot.

    Também registra ``_FiltroDeSegredos`` nos handlers instalados por
    ``setup_adk_logger`` (via ``logging.basicConfig`` na raiz) — ver a
    docstring da classe para o que isso cobre e o que não cobre.
    """
    setup_adk_logger(level=_resolve_level())
    filtro = _FiltroDeSegredos()
    for handler in logging.getLogger().handlers:
        if not any(isinstance(f, _FiltroDeSegredos) for f in handler.filters):
            handler.addFilter(filtro)


def resolved_plugins() -> list[str]:
    """Nomes qualificados dos plugins nativos a registrar via extra_plugins.

    Controlado por ADK_LOG_PLUGIN:
        off      → nenhum plugin.
        console  → LoggingPlugin (loga tudo no stdout). [default]
        file     → DebugLoggingPlugin (YAML estruturado por invocação).
    """
    mode = os.environ.get("ADK_LOG_PLUGIN", "console").strip().lower()
    if mode == "off":
        return []
    if mode == "file":
        return ["shared.observability.debug_logging_plugin"]
    # default: console
    return ["google.adk.plugins.LoggingPlugin"]


_ATRIBUTOS_OPENINFERENCE_A_REDIGIR = re.compile(
    r"^(input\.value|output\.value|"
    r"llm\.(?:input|output)_messages\.\d+\.message\.content)$"
)


def setup_langfuse() -> None:
    """Ativa tracing externo via Langfuse + OpenInference, opt-in.

    NÃO roda por padrão e não é chamada automaticamente por nada neste
    módulo — quem quiser tracing externo chama isso explicitamente no boot
    (ex.: app/main.py). Sem ``LANGFUSE_PUBLIC_KEY`` definida, é um no-op
    completo: nem ``langfuse`` nem ``openinference``/``opentelemetry`` são
    importados, então declarar a env var é a única forma de essas
    dependências saírem do estado "instaladas mas nunca tocadas" em que
    foram encontradas (nenhum import delas existia em nenhum lugar do
    projeto antes desta função).

    Usa ``mask_otel_spans`` do SDK Langfuse (não o parâmetro ``mask``, mais
    simples): ``GoogleADKInstrumentor`` é um instrumentador OpenTelemetry
    genérico que cria ``ReadableSpan`` diretamente, sem passar pela API
    nativa ``Span``/``Generation`` do Langfuse — só ``mask`` alcançaria
    dados criados por essa API nativa, então spans do OpenInference
    passariam por ele sem qualquer redação. ``mask_otel_spans`` opera nos
    atributos do span já exportado, então cobre esse caso.

    Redige os únicos atributos que ``openinference-instrumentation-google-adk``
    grava sem qualquer redação própria (ver ``_wrappers.py`` do pacote
    instalado): ``input.value``, ``output.value`` (dump JSON completo de
    argumentos/resultados de tool call) e
    ``llm.input_messages.<i>.message.content`` /
    ``llm.output_messages.<i>.message.content`` (conteúdo completo de cada
    mensagem de prompt/resposta). Reaproveita ``redigir_segredos`` — mesma
    função usada em pytest_runner e no sanitizer do QA — em vez de inventar
    um novo padrão de redação.

    Qualquer exceção na inicialização (SDK incompatível, rede indisponível,
    credencial inválida, instrumentação duplicada, etc.) é capturada: loga
    um warning e a função retorna sem tracing, em vez de derrubar o boot do
    app por causa de uma feature opt-in de observabilidade. Verificado que,
    na ordem de import real de produção (``import app.main``, que descobre e
    importa todos os agentes em ``src/agents/`` via ``get_fast_api_app``), o
    import de ``langfuse``/``langchain_core`` funciona sem conflito — o
    ``TypeError`` de MRO só foi observado dentro do processo da suíte de
    testes (ver ``tests/unit/test_observability_guardrails.py``). Esse
    try/except fica de qualquer forma, como rede de segurança geral.
    """
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        return

    try:
        from langfuse import Langfuse
        from langfuse.types import MaskOtelSpansParams, MaskOtelSpansResult, OtelSpanPatch
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        def _mask_otel_spans(
            *, params: MaskOtelSpansParams
        ) -> MaskOtelSpansResult | None:
            patches = {
                identificador: OtelSpanPatch(set_attributes=redigidos)
                for identificador, span in params.spans.items()
                if (redigidos := redigir_atributos_openinference(span.attributes))
            }
            return MaskOtelSpansResult(span_patches=patches) if patches else None

        Langfuse(mask_otel_spans=_mask_otel_spans)
        GoogleADKInstrumentor().instrument()
    except Exception as exc:  # noqa: BLE001 — feature opt-in não pode derrubar o boot
        logger.warning("Langfuse desabilitado: %s", exc)
        return


def redigir_atributos_openinference(atributos) -> dict[str, str]:
    """Núcleo puro da redação usada por ``setup_langfuse``, extraído para ser
    testável sem precisar importar ``langfuse``/``opentelemetry`` de verdade
    (ver nota em ``tests/unit/test_observability_guardrails.py`` sobre o
    conflito de import entre ``langfuse`` e ``langchain_core`` neste
    ambiente). Recebe qualquer mapeamento chave→valor (duck typing — não
    exige ``OtelSpanData`` real) e devolve só as chaves que batem com
    ``input.value``/``output.value``/``llm.*_messages.<i>.message.content``,
    com o valor já passado por ``redigir_segredos``. Mapeamento vazio quando
    nada bate.
    """
    return {
        chave: redigir_segredos(str(valor))
        for chave, valor in atributos.items()
        if _ATRIBUTOS_OPENINFERENCE_A_REDIGIR.match(chave)
    }
