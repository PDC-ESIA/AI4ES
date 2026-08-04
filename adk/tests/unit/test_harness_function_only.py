"""Testes unitários para o mode='function_only' do harness de execução.

Valida que:
- Estágio 4 (healthcheck) é pulado e app_ok é forçado a True
- Estágio 7 (probes HTTP) é pulado
- Estágio 6 (pytest) é desbloqueado mesmo sem servidor web
- Mode 'web' (default) mantém comportamento original
"""

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shared.tools.harness_execucao import executar_harness_validacao, executar_harness_tool


@pytest.fixture
def workspace_funcional(tmp_path):
    """Cria workspace mínimo para mode=function_only."""
    coder_dir = tmp_path / "coder"
    coder_dir.mkdir()

    # Arquivo Python mínimo (estágio 1 exige *.py)
    (coder_dir / "solution.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )

    # Dockerfile mínimo
    (coder_dir / "Dockerfile").write_text(
        "FROM python:3.12-slim\nWORKDIR /app\nCOPY . /app/\n"
        'CMD ["python", "-c", "print(\'ok\')"]\n',
        encoding="utf-8",
    )

    # Task JSON
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    task = {
        "task_id": "test_func",
        "description": "Test function",
        "acceptance_criteria": ["add(1, 2) returns 3"],
    }
    (tasks_dir / "test_func.json").write_text(
        json.dumps(task), encoding="utf-8",
    )

    exec_dir = tmp_path / "execution"
    exec_dir.mkdir()

    return coder_dir, exec_dir, tasks_dir


class TestFunctionOnlyMode:
    """Testa o mode='function_only' do harness."""

    @patch("shared.tools.harness_execucao.docker")
    def test_estagio_4_pulado_e_app_ok_true(self, mock_docker, workspace_funcional):
        """Estágio 4 deve ser PULADO e app_ok forçado a True em function_only."""
        coder_dir, exec_dir, tasks_dir = workspace_funcional

        # Mock Docker para não depender do daemon
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.logs.return_value = b""
        mock_container.attrs = {"State": {"ExitCode": 0}}
        mock_container.reload = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_client.images.build.return_value = (MagicMock(), [{"stream": "ok"}])

        result = executar_harness_validacao(
            task_id="test_func",
            iteration=1,
            mode="function_only",
            coder_base_dir=coder_dir,
            execution_base_dir=exec_dir,
            tasks_base_dir=tasks_dir,
        )

        stages = {s["stage"]: s for s in result["stages"]}

        # Estágio 4 deve estar pulado
        assert stages["inicializacao_aplicacao"]["status"] == "pulado"
        assert "function_only" in stages["inicializacao_aplicacao"]["summary"]

        # Estágio 7 deve estar pulado
        assert stages["validacoes_work_item"]["status"] == "pulado"
        assert "function_only" in stages["validacoes_work_item"]["summary"]

    @patch("shared.tools.harness_execucao.docker")
    def test_estagio_6_desbloqueado(self, mock_docker, workspace_funcional):
        """Estágio 6 (pytest) deve executar mesmo sem servidor web."""
        coder_dir, exec_dir, tasks_dir = workspace_funcional

        # Adiciona um teste ao workspace
        (coder_dir / "test_solution.py").write_text(
            "def test_add():\n"
            "    from solution import add\n"
            "    assert add(1, 2) == 3\n",
            encoding="utf-8",
        )

        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.logs.return_value = b""
        mock_container.attrs = {"State": {"ExitCode": 0}}
        mock_container.reload = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_client.images.build.return_value = (MagicMock(), [{"stream": "ok"}])

        # Mock exec_run para simular pytest passando
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=(b"1 passed in 0.01s", None),
        )

        result = executar_harness_validacao(
            task_id="test_func",
            iteration=1,
            mode="function_only",
            coder_base_dir=coder_dir,
            execution_base_dir=exec_dir,
            tasks_base_dir=tasks_dir,
        )

        stages = {s["stage"]: s for s in result["stages"]}

        # Estágio 6 NÃO deve estar pulado
        assert stages["testes_automatizados"]["status"] != "pulado"

    def test_mode_web_default_validacao(self):
        """Verifica que o mode default é 'web' em executar_harness_validacao."""
        sig = inspect.signature(executar_harness_validacao)
        assert sig.parameters["mode"].default == "web"

    def test_mode_web_default_tool(self):
        """Verifica que o mode default é 'web' em executar_harness_tool."""
        sig = inspect.signature(executar_harness_tool)
        assert sig.parameters["mode"].default == "web"
