"""Guard rails de observabilidade (P4): filtro de log e setup_langfuse opt-in.

NOTA sobre o que NÃO é testado aqui end-to-end: `obs.setup_langfuse()`
importa o pacote `langfuse` de verdade quando LANGFUSE_PUBLIC_KEY está
definida. Fazer esse import dentro do MESMO processo pytest usado pela
suíte completa deste projeto (que já carrega `langchain_core` de outros
jeitos, via os agentes que usam langchain) dispara, de forma determinística
neste ambiente (Python 3.14.7 + as versões pinadas em pyproject.toml), um
`TypeError: Cannot create a consistent method resolution order` — o próprio
`langfuse/_utils/serializer.py` importa `langchain_core.load.serializable.
Serializable`, e essa segunda inicialização de `langchain_core` no meio da
suíte colide com a already-loaded. Confirmado rodando `pytest tests/ -q`
duas vezes com um teste que fazia esse import de verdade: falha idêntica e
determinística nas duas rodadas, e a suíte completa fica limpa assim que o
import de `langfuse` deixa de acontecer no processo de teste.

Por isso a lógica de redação foi extraída para `redigir_atributos_
openinference` (função pura, duck-typed, sem depender de nenhum tipo real
do langfuse) — é isso que os testes abaixo exercitam. O fiozinho que resta
em `setup_langfuse()` (só chamar `Langfuse(...)` e
`GoogleADKInstrumentor().instrument()` com essa máscara) foi verificado
manualmente rodando `setup_langfuse()` de verdade num processo Python
isolado (fora da suíte) antes deste commit — ver mensagem do PR.
"""

import io
import logging

import shared.observability as obs


# ---------------------------------------------------------------------------
# _FiltroDeSegredos
# ---------------------------------------------------------------------------


def _logger_com_filtro(nome: str) -> tuple[logging.Logger, io.StringIO]:
    logger = logging.getLogger(nome)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.addFilter(obs._FiltroDeSegredos())
    logger.addHandler(handler)
    logger.propagate = False
    return logger, buf


def test_filtro_redige_segredo_na_mensagem():
    logger, buf = _logger_com_filtro("test_filtro_msg")
    logger.info("token = ghp_supersecreto123")
    assert "ghp_supersecreto123" not in buf.getvalue()
    assert "[REDACTED]" in buf.getvalue()


def test_filtro_redige_segredo_em_args_posicionais():
    logger, buf = _logger_com_filtro("test_filtro_args")
    logger.info("valor recebido: %s", "api_key=sk-proj-real123")
    assert "sk-proj-real123" not in buf.getvalue()


def test_filtro_nao_altera_mensagem_sem_segredo():
    logger, buf = _logger_com_filtro("test_filtro_limpo")
    logger.info("3 passed, 0 failed")
    assert "3 passed, 0 failed" in buf.getvalue()


def test_setup_logging_registra_filtro_uma_unica_vez(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    obs.setup_logging()
    obs.setup_logging()  # idempotência: não deve duplicar o filtro

    root = logging.getLogger()
    for handler in root.handlers:
        quantidade = sum(
            1 for f in handler.filters if isinstance(f, obs._FiltroDeSegredos)
        )
        assert quantidade <= 1


# ---------------------------------------------------------------------------
# setup_langfuse — opt-in via LANGFUSE_PUBLIC_KEY
# ---------------------------------------------------------------------------


def test_setup_langfuse_e_no_op_sem_env_var(monkeypatch):
    import sys

    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    for modulo in ("langfuse", "openinference.instrumentation.google_adk"):
        sys.modules.pop(modulo, None)

    obs.setup_langfuse()

    assert "langfuse" not in sys.modules
    assert "openinference.instrumentation.google_adk" not in sys.modules


def test_redigir_atributos_openinference_redige_os_alvos():
    atributos = {
        "input.value": "api_key=sk-real-vazando-123 outros_dados=ok",
        "output.value": "resposta com token = ghp_real_secret",
        "llm.input_messages.0.message.content": "prompt contendo password: hunter2real",
        "llm.output_messages.2.message.content": "resposta com secret = zzz_real",
        "llm.model_name": "gpt-4",  # não deve ser tocado
        "tool.name": "executar_pytest_tool",  # não deve ser tocado
    }

    redigidos = obs.redigir_atributos_openinference(atributos)

    assert set(redigidos) == {
        "input.value",
        "output.value",
        "llm.input_messages.0.message.content",
        "llm.output_messages.2.message.content",
    }
    assert "sk-real-vazando-123" not in redigidos["input.value"]
    assert "ghp_real_secret" not in redigidos["output.value"]
    assert "hunter2real" not in redigidos["llm.input_messages.0.message.content"]
    assert "zzz_real" not in redigidos["llm.output_messages.2.message.content"]


def test_redigir_atributos_openinference_vazio_quando_nada_bate():
    atributos = {"tool.name": "executar_pytest_tool", "llm.model_name": "gpt-4"}
    assert obs.redigir_atributos_openinference(atributos) == {}


def test_setup_langfuse_excecao_na_inicializacao_nao_propaga(monkeypatch, caplog):
    """Injeta módulos `langfuse`/`openinference` FALSOS via sys.modules — não
    importa os pacotes reais (evita o conflito de import descrito na nota do
    topo deste arquivo) — só para forçar `Langfuse(...)` a levantar e provar
    que setup_langfuse() não propaga a exceção, e sim loga um warning.
    """
    import sys
    import types

    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-teste-fake")

    class _LangfuseQueFalha:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("falha simulada de inicializacao do Langfuse")

    fake_langfuse = types.ModuleType("langfuse")
    fake_langfuse.Langfuse = _LangfuseQueFalha

    fake_langfuse_types = types.ModuleType("langfuse.types")
    fake_langfuse_types.MaskOtelSpansParams = object
    fake_langfuse_types.MaskOtelSpansResult = object
    fake_langfuse_types.OtelSpanPatch = object

    class _FakeInstrumentor:
        def instrument(self, **_kwargs):
            return None

    fake_openinference = types.ModuleType("openinference")
    fake_openinference_instrumentation = types.ModuleType(
        "openinference.instrumentation"
    )
    fake_openinference_google_adk = types.ModuleType(
        "openinference.instrumentation.google_adk"
    )
    fake_openinference_google_adk.GoogleADKInstrumentor = _FakeInstrumentor

    for nome, modulo in (
        ("langfuse", fake_langfuse),
        ("langfuse.types", fake_langfuse_types),
        ("openinference", fake_openinference),
        ("openinference.instrumentation", fake_openinference_instrumentation),
        ("openinference.instrumentation.google_adk", fake_openinference_google_adk),
    ):
        monkeypatch.setitem(sys.modules, nome, modulo)

    with caplog.at_level(logging.WARNING, logger="shared.observability"):
        obs.setup_langfuse()  # não deve levantar

    assert any(
        "Langfuse desabilitado" in registro.message for registro in caplog.records
    )
