"""Testes do sandbox de execução (`shared/execution/sandbox.py`).

Foco no `DirectSandbox` (execução real de subprocess, sem mocks): setup copia o
artefato, exec captura saída/exit-code, timeout é honrado, env é limpo (não
vaza variáveis do host), serviço em segundo plano expõe logs e cleanup encerra
tudo. O `DockerSandbox` é coberto com o cliente Docker mockado (sem daemon). A
factory `create_sandbox` também é coberta.
"""

from unittest.mock import MagicMock, patch

import pytest

from shared.execution.sandbox import (
    CommandResult,
    DirectSandbox,
    DockerSandbox,
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


def test_create_sandbox_docker_retorna_docker_sandbox():
    sb = create_sandbox("docker")
    assert isinstance(sb, DockerSandbox)


def test_create_sandbox_desconhecido():
    with pytest.raises(ValueError):
        create_sandbox("firecracker")


# ---------------------------------------------------------------------------
# DockerSandbox — cliente Docker mockado (sem daemon real)
# ---------------------------------------------------------------------------

class _FakeExec:
    """Imita o ExecResult do docker-py (exit_code + output)."""

    def __init__(self, exit_code=0, stdout=b"", stderr=b""):
        self.exit_code = exit_code
        self.output = (stdout, stderr)


def _fake_docker_client():
    client = MagicMock()
    container = MagicMock()
    container.exec_run.return_value = _FakeExec(0, b"ok", b"")
    client.containers.run.return_value = container
    image = MagicMock()
    client.images.build.return_value = (image, [])
    return client, container


def test_docker_sandbox_satisfaz_protocolo():
    assert isinstance(DockerSandbox(), Sandbox)


def test_docker_sandbox_setup_sem_dockerfile_monta_volume(tmp_path):
    src = _make_artifact(tmp_path)
    client, container = _fake_docker_client()
    sb = DockerSandbox(port=8000)
    with patch("shared.execution.sandbox.docker.from_env", return_value=client):
        sb.setup(src)
    # Sem Dockerfile → não constrói imagem, monta volume e publica a porta.
    client.images.build.assert_not_called()
    _, kwargs = client.containers.run.call_args
    assert kwargs["volumes"] is not None
    assert kwargs["ports"] == {"8000/tcp": ("0.0.0.0", 8000)}
    assert kwargs["working_dir"] == "/app"


def test_docker_sandbox_setup_com_dockerfile_constroi_imagem(tmp_path):
    src = _make_artifact(tmp_path)
    (src / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    client, container = _fake_docker_client()
    sb = DockerSandbox()
    with patch("shared.execution.sandbox.docker.from_env", return_value=client):
        sb.setup(src)
    # Com Dockerfile → constrói a imagem e NÃO monta volume (código assado).
    client.images.build.assert_called_once()
    _, kwargs = client.containers.run.call_args
    assert kwargs["volumes"] is None


def test_docker_sandbox_exec_wrap_timeout(tmp_path):
    src = _make_artifact(tmp_path)
    client, container = _fake_docker_client()
    container.exec_run.return_value = _FakeExec(0, b"saida-do-comando", b"")
    sb = DockerSandbox()
    with patch("shared.execution.sandbox.docker.from_env", return_value=client):
        sb.setup(src)
        res = sb.exec("echo oi", timeout=30)
    assert isinstance(res, CommandResult)
    assert res.exit_code == 0
    assert "saida-do-comando" in res.stdout
    # O comando é embrulhado com timeout(1) e workdir /app.
    args, kwargs = container.exec_run.call_args
    shell = args[0][-1]
    assert "timeout 30" in shell
    assert kwargs["workdir"] == "/app"


def test_docker_sandbox_exec_timeout_exit_124(tmp_path):
    src = _make_artifact(tmp_path)
    client, container = _fake_docker_client()
    container.exec_run.return_value = _FakeExec(124, b"", b"")
    sb = DockerSandbox()
    with patch("shared.execution.sandbox.docker.from_env", return_value=client):
        sb.setup(src)
        res = sb.exec("sleep 99", timeout=1)
    assert res.timed_out is True


def test_docker_sandbox_start_service_e_logs(tmp_path):
    src = _make_artifact(tmp_path)
    client, container = _fake_docker_client()
    sb = DockerSandbox()
    with patch("shared.execution.sandbox.docker.from_env", return_value=client):
        sb.setup(src)
        sb.start_service("uvicorn app.main:app")
        # start_service dispara exec em segundo plano (detach=True).
        _, start_kwargs = container.exec_run.call_args
        assert start_kwargs["detach"] is True
        container.exec_run.return_value = _FakeExec(0, b"servico-no-ar", b"")
        assert "servico-no-ar" in sb.logs()


def test_docker_sandbox_cleanup_remove_container(tmp_path):
    src = _make_artifact(tmp_path)
    client, container = _fake_docker_client()
    sb = DockerSandbox()
    with patch("shared.execution.sandbox.docker.from_env", return_value=client):
        sb.setup(src)
        root = sb.root
        sb.cleanup()
    container.remove.assert_called_once()
    assert not root.exists()


def test_docker_sandbox_exec_antes_do_setup_levanta():
    sb = DockerSandbox()
    with pytest.raises(RuntimeError):
        sb.exec("echo oi", timeout=5)
