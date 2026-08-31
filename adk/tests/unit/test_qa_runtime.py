"""Testes do runtime que sobe a aplicação para o QA navegar (PoC issue #394).

O que importa aqui é que NENHUM caminho levante e que o sandbox seja SEMPRE
encerrado: quem chama está no meio de uma rodada do loop, e um vazamento de
processo aqui deixaria a porta ocupada para a rodada seguinte — que é a origem
do pior modo de falha do módulo (navegar um artefato antigo).
"""

from __future__ import annotations

import json

import pytest
import requests

from shared.execution import qa_runtime


class _SandboxFalso:
    """Registra o que foi pedido e se o cleanup aconteceu."""

    def __init__(self, exit_code: int = 0, ao_iniciar: Exception | None = None):
        self.exit_code = exit_code
        self.ao_iniciar = ao_iniciar
        self.comandos: list[str] = []
        self.servico: str | None = None
        self.limpou = False

    def setup(self, source_dir):
        self.origem = source_dir

    def exec(self, command, *, timeout, env=None):
        self.comandos.append(command)
        from shared.execution.sandbox import CommandResult

        return CommandResult(exit_code=self.exit_code, stdout="", stderr="")

    def start_service(self, command, *, env=None):
        if self.ao_iniciar is not None:
            raise self.ao_iniciar
        self.servico = command

    def cleanup(self):
        self.limpou = True


def _manifesto(tmp_path, **overrides) -> None:
    dados = {
        "surface": "service",
        "build": ["pip install -r requirements.txt"],
        "run": "uvicorn app:app",
        "port": 8123,
        "healthcheck": "/",
    }
    dados.update(overrides)
    (tmp_path / "run.json").write_text(json.dumps(dados), encoding="utf-8")


@pytest.fixture
def sandbox(monkeypatch):
    """Instala um sandbox falso e devolve o objeto criado."""
    criado = _SandboxFalso()
    monkeypatch.setattr(qa_runtime, "create_sandbox", lambda *a, **k: criado)
    monkeypatch.setattr(qa_runtime.time, "sleep", lambda _: None)
    return criado


def _respostas(monkeypatch, *sequencia):
    """Programa as respostas de `requests.get`, em ordem.

    Cada item é um status HTTP ou uma exceção a levantar.
    """
    restantes = list(sequencia)

    class _Resposta:
        def __init__(self, status):
            self.status_code = status

    def _get(*_args, **_kwargs):
        atual = restantes.pop(0) if restantes else requests.RequestException("fim")
        if isinstance(atual, Exception):
            raise atual
        return _Resposta(atual)

    monkeypatch.setattr(qa_runtime.requests, "get", _get)


# ---------------------------------------------------------------------------
# Não aplicabilidade — barata e explícita, sem gastar build
# ---------------------------------------------------------------------------


def test_manifesto_ausente_nao_estoura(tmp_path):
    with qa_runtime.aplicacao_no_ar(tmp_path) as aplicacao:
        assert aplicacao.no_ar is False
        assert "Manifesto" in aplicacao.motivo


@pytest.mark.parametrize("surface", ["command", "none"])
def test_artefato_sem_interface_nao_gasta_build(tmp_path, monkeypatch, surface):
    """Sem serviço de rede não há o que navegar — e nada deve ser construído."""
    dados = {"surface": surface, "build": ["make"], "run": "./cli", "test": ["pytest"]}
    (tmp_path / "run.json").write_text(json.dumps(dados), encoding="utf-8")
    monkeypatch.setattr(
        qa_runtime,
        "create_sandbox",
        lambda *a, **k: pytest.fail("sandbox criado para artefato sem interface"),
    )

    with qa_runtime.aplicacao_no_ar(tmp_path) as aplicacao:
        assert aplicacao.no_ar is False
        assert surface in aplicacao.motivo


# ---------------------------------------------------------------------------
# Caminho feliz e o guarda contra artefato remanescente
# ---------------------------------------------------------------------------


def test_aplicacao_sobe_e_entrega_a_url(tmp_path, sandbox, monkeypatch):
    _manifesto(tmp_path)
    # 1ª chamada: pré-checagem da porta (livre). 2ª: healthcheck (viva).
    _respostas(monkeypatch, requests.RequestException("livre"), 200)

    with qa_runtime.aplicacao_no_ar(tmp_path) as aplicacao:
        assert aplicacao.no_ar is True
        assert aplicacao.base_url == "http://localhost:8123"

    assert sandbox.servico == "uvicorn app:app"
    assert sandbox.limpou is True


def test_porta_ja_ocupada_aborta_sem_navegar(tmp_path, sandbox, monkeypatch):
    """O pior modo de falha do módulo: navegar um artefato antigo.

    Um serviço remanescente de uma rodada anterior responderia ao healthcheck e o
    QA avaliaria o CÓDIGO ANTIGO como se fosse o novo. Abortar é obrigatório —
    um falso sinal desses é pior que não medir.
    """
    _manifesto(tmp_path)
    _respostas(monkeypatch, 200)  # já tem alguém atendendo antes de subirmos

    with qa_runtime.aplicacao_no_ar(tmp_path) as aplicacao:
        assert aplicacao.no_ar is False
        assert "ocupada" in aplicacao.motivo

    # A checagem vem ANTES do build: nada chega a ser construído nem iniciado,
    # então também não há sandbox a limpar. Descobrir isso depois do build
    # desperdiçaria até `_BUILD_TIMEOUT` para chegar à mesma conclusão.
    assert sandbox.servico is None, "subiu o serviço apesar da porta ocupada"
    assert sandbox.comandos == [], "gastou build antes de detectar a porta ocupada"


def test_app_que_nao_responde_vira_motivo(tmp_path, sandbox, monkeypatch):
    _manifesto(tmp_path)
    _respostas(monkeypatch, requests.RequestException("livre"))

    with qa_runtime.aplicacao_no_ar(tmp_path) as aplicacao:
        assert aplicacao.no_ar is False
        assert "não respondeu" in aplicacao.motivo

    assert sandbox.limpou is True


def test_http_de_erro_no_healthcheck_nao_conta_como_viva(
    tmp_path, sandbox, monkeypatch
):
    """App de pé mas que não serve: navegar produziria falha de critério falsa."""
    _manifesto(tmp_path)
    _respostas(monkeypatch, requests.RequestException("livre"), 500)

    with qa_runtime.aplicacao_no_ar(tmp_path) as aplicacao:
        assert aplicacao.no_ar is False
        assert "500" in aplicacao.motivo


# ---------------------------------------------------------------------------
# Falhas de infraestrutura — sempre motivo, nunca exceção
# ---------------------------------------------------------------------------


def test_build_que_falha_vira_motivo(tmp_path, monkeypatch):
    quebrado = _SandboxFalso(exit_code=1)
    monkeypatch.setattr(qa_runtime, "create_sandbox", lambda *a, **k: quebrado)
    _manifesto(tmp_path)

    with qa_runtime.aplicacao_no_ar(tmp_path) as aplicacao:
        assert aplicacao.no_ar is False
        assert "build do QA falhou" in aplicacao.motivo

    assert quebrado.servico is None
    assert quebrado.limpou is True


def test_falha_ao_iniciar_o_servico_vira_motivo(tmp_path, monkeypatch):
    quebrado = _SandboxFalso(ao_iniciar=OSError("porta em uso"))
    monkeypatch.setattr(qa_runtime, "create_sandbox", lambda *a, **k: quebrado)
    monkeypatch.setattr(qa_runtime.time, "sleep", lambda _: None)
    _manifesto(tmp_path)
    _respostas(monkeypatch, requests.RequestException("livre"))

    with qa_runtime.aplicacao_no_ar(tmp_path) as aplicacao:
        assert aplicacao.no_ar is False
        assert "iniciar o serviço" in aplicacao.motivo

    assert quebrado.limpou is True


def test_sandbox_indisponivel_vira_motivo(tmp_path, monkeypatch):
    def _explode(*_a, **_k):
        raise RuntimeError("docker fora do ar")

    monkeypatch.setattr(qa_runtime, "create_sandbox", _explode)
    _manifesto(tmp_path)

    with qa_runtime.aplicacao_no_ar(tmp_path) as aplicacao:
        assert aplicacao.no_ar is False
        assert "sandbox do QA" in aplicacao.motivo


def test_cleanup_acontece_mesmo_com_excecao_no_bloco(tmp_path, sandbox, monkeypatch):
    """O sandbox não pode vazar por uma falha de quem consome a URL."""
    _manifesto(tmp_path)
    _respostas(monkeypatch, requests.RequestException("livre"), 200)

    with pytest.raises(ValueError):
        with qa_runtime.aplicacao_no_ar(tmp_path):
            raise ValueError("falha do consumidor")

    assert sandbox.limpou is True


def test_cleanup_que_falha_nao_derruba_a_rodada(tmp_path, monkeypatch):
    class _CleanupQuebrado(_SandboxFalso):
        def cleanup(self):
            raise OSError("não consegui limpar")

    monkeypatch.setattr(
        qa_runtime, "create_sandbox", lambda *a, **k: _CleanupQuebrado()
    )
    monkeypatch.setattr(qa_runtime.time, "sleep", lambda _: None)
    _manifesto(tmp_path)
    _respostas(monkeypatch, requests.RequestException("livre"), 200)

    with qa_runtime.aplicacao_no_ar(tmp_path) as aplicacao:
        assert aplicacao.no_ar is True
