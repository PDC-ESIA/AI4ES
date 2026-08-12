"""Testes do sandbox de execução (`shared/execution/sandbox.py`).

Foco no `DirectSandbox` (execução real de subprocess, sem mocks): setup copia o
artefato, exec captura saída/exit-code, timeout é honrado, env é limpo (não
vaza variáveis do host), serviço em segundo plano expõe logs e cleanup encerra
tudo. A factory `create_sandbox` também é coberta.
"""

import pytest

from shared.execution.sandbox import (
    CommandResult,
    DirectSandbox,
    Sandbox,
    create_sandbox,
)


def _make_artifact(tmp_path):
    src = tmp_path / "artifact"
    src.mkdir()
    (src / "hello.txt").write_text("oi", encoding="utf-8")
    return src


# ---------------------------------------------------------------------------
# DirectSandbox — ciclo de vida e execução
# ---------------------------------------------------------------------------

def test_setup_copia_artefato(tmp_path):
    src = _make_artifact(tmp_path)
    sb = DirectSandbox()
    try:
        sb.setup(src)
        assert (sb.root / "hello.txt").read_text(encoding="utf-8") == "oi"
    finally:
        sb.cleanup()


def test_exec_captura_stdout_e_exit_code(tmp_path):
    src = _make_artifact(tmp_path)
    sb = DirectSandbox()
    try:
        sb.setup(src)
        res = sb.exec("echo ola-mundo", timeout=10)
        assert isinstance(res, CommandResult)
        assert res.exit_code == 0
        assert "ola-mundo" in res.stdout
        assert res.timed_out is False
    finally:
        sb.cleanup()


def test_exec_exit_code_nao_zero(tmp_path):
    src = _make_artifact(tmp_path)
    sb = DirectSandbox()
    try:
        sb.setup(src)
        res = sb.exec("exit 3", timeout=10)
        assert res.exit_code == 3
    finally:
        sb.cleanup()


def test_exec_roda_no_workdir_do_artefato(tmp_path):
    src = _make_artifact(tmp_path)
    sb = DirectSandbox()
    try:
        sb.setup(src)
        res = sb.exec("cat hello.txt", timeout=10)
        assert res.stdout.strip() == "oi"
    finally:
        sb.cleanup()


def test_exec_timeout(tmp_path):
    src = _make_artifact(tmp_path)
    sb = DirectSandbox()
    try:
        sb.setup(src)
        res = sb.exec("sleep 5", timeout=1)
        assert res.timed_out is True
        assert res.exit_code is None
    finally:
        sb.cleanup()


def test_exec_env_limpo_nao_vaza_host(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_LEAK", "senha123")
    src = _make_artifact(tmp_path)
    sb = DirectSandbox()
    try:
        sb.setup(src)
        res = sb.exec('echo "[${SECRET_LEAK}]"', timeout=10)
        assert res.stdout.strip() == "[]"  # var do host não vaza
    finally:
        sb.cleanup()


def test_exec_env_extra_disponivel(tmp_path):
    src = _make_artifact(tmp_path)
    sb = DirectSandbox()
    try:
        sb.setup(src)
        res = sb.exec('echo "[${MINHA_VAR}]"', timeout=10, env={"MINHA_VAR": "abc"})
        assert res.stdout.strip() == "[abc]"
    finally:
        sb.cleanup()


def test_workdir_subpath(tmp_path):
    src = tmp_path / "artifact"
    (src / "sub").mkdir(parents=True)
    (src / "sub" / "marca.txt").write_text("aqui", encoding="utf-8")
    sb = DirectSandbox(workdir_subpath="sub")
    try:
        sb.setup(src)
        res = sb.exec("cat marca.txt", timeout=10)
        assert res.stdout.strip() == "aqui"
    finally:
        sb.cleanup()


def test_start_service_logs_e_cleanup(tmp_path):
    src = _make_artifact(tmp_path)
    sb = DirectSandbox()
    sb.setup(src)
    root = sb.root
    # Serviço trivial que imprime e segue vivo.
    sb.start_service("echo servico-no-ar; sleep 30")
    # Aguarda o log materializar.
    import time

    for _ in range(20):
        if "servico-no-ar" in sb.logs():
            break
        time.sleep(0.1)
    assert "servico-no-ar" in sb.logs()
    sb.cleanup()
    # cleanup remove o diretório temporário.
    assert not root.exists()


def test_root_antes_do_setup_levanta():
    sb = DirectSandbox()
    with pytest.raises(RuntimeError):
        _ = sb.root


def test_direct_sandbox_satisfaz_protocolo():
    assert isinstance(DirectSandbox(), Sandbox)


# ---------------------------------------------------------------------------
# create_sandbox — factory
# ---------------------------------------------------------------------------

def test_create_sandbox_direct():
    sb = create_sandbox("direct")
    assert isinstance(sb, DirectSandbox)


def test_create_sandbox_docker_ainda_nao_habilitado():
    with pytest.raises(NotImplementedError, match="Fase 4"):
        create_sandbox("docker")


def test_create_sandbox_desconhecido():
    with pytest.raises(ValueError):
        create_sandbox("firecracker")
