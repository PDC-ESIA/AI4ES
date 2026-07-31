"""Tests para o cr_executor do workflow_coding_review.

Cobertura:
- Agent wiring: nome, tools, output_key
- _detect_entrypoint: detecta main.py em vários layouts
- _detect_requirements: encontra requirements.txt
- _generate_dockerfile: gera Dockerfile válido para o workspace
- tool_listar_arquivos_coder: lista arquivos corretamente
- tool_verificar_docker: verifica docker daemon (mocado)
- tool_executar_em_docker: fluxo completo mocando docker client
- Integração com LoopAgent: coder.instruction contém {execution_result?}
"""

import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def executor_module(tmp_path, monkeypatch):
    """Reimporta cr_executor (+ docker_executor) com workspace temporário.

    docker_executor.py computa _CODER_WS/_EXEC_WS a nível de módulo — precisa
    ser recarregado ANTES de cr_executor.py para que os nomes re-exportados
    (cr_executor._CODER_WS etc.) reflitam o novo WORKSPACE_OUTPUT_DIR.
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from shared.tools.coding_review import docker_executor
    from src.agents.workflow_coding_review import cr_executor

    importlib.reload(docker_executor)
    importlib.reload(cr_executor)
    return cr_executor


@pytest.fixture
def coder_ws(executor_module):
    """Retorna o workspace do coder (já criado pelo reload)."""
    ws = Path(executor_module._CODER_WS)
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def exec_ws(executor_module):
    """Retorna o workspace do executor (já criado pelo reload)."""
    ws = Path(executor_module._EXEC_WS)
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def mock_tool_context():
    """Mock de ToolContext com state dict e actions."""
    ctx = MagicMock()
    ctx.state = {}
    ctx.actions = MagicMock()
    ctx.actions.escalate = False
    return ctx


# ===========================================================================
# Agent wiring
# ===========================================================================


def test_executor_agent_name(executor_module):
    assert executor_module.agent.name == "cr_executor_agent"


def test_executor_agent_output_key(executor_module):
    assert executor_module.agent.output_key == "execution_result"


def test_executor_agent_tem_4_tools(executor_module):
    """Executor deve ter 4 tools: verificar_docker, listar_arquivos, executar_em_docker, exit_loop."""
    tools = executor_module.agent.tools
    assert len(tools) == 4


def test_executor_agent_tem_exit_loop_tool(executor_module):
    """tool_exit_loop_se_sucesso (guarded) deve estar nas tools do executor."""
    tools = executor_module.agent.tools
    tool_names = []
    for t in tools:
        if hasattr(t, "func"):
            tool_names.append(t.func.__name__)
        elif hasattr(t, "name"):
            tool_names.append(t.name)
    assert "tool_exit_loop_se_sucesso" in tool_names


# ===========================================================================
# _detect_entrypoint
# ===========================================================================


def test_detect_entrypoint_app_main(executor_module, coder_ws):
    """Detecta app/main.py como entrypoint."""
    (coder_ws / "app").mkdir()
    (coder_ws / "app" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    result = executor_module._detect_entrypoint(coder_ws)
    assert result == "app/main.py"


def test_detect_entrypoint_main_py_raiz(executor_module, coder_ws):
    """Detecta main.py na raiz."""
    (coder_ws / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    result = executor_module._detect_entrypoint(coder_ws)
    assert result == "main.py"


def test_detect_entrypoint_busca_fastapi_em_rglob(executor_module, coder_ws):
    """Quando nenhum candidato match, busca FastAPI via rglob."""
    (coder_ws / "src" / "server").mkdir(parents=True)
    (coder_ws / "src" / "server" / "api.py").write_text("from fastapi import FastAPI")
    result = executor_module._detect_entrypoint(coder_ws)
    assert "api.py" in result


def test_detect_entrypoint_fallback_main(executor_module, coder_ws):
    """Quando nenhum .py tem FastAPI, retorna fallback 'main.py'."""
    (coder_ws / "utils.py").write_text("# nada aqui")
    result = executor_module._detect_entrypoint(coder_ws)
    assert result == "main.py"


# ===========================================================================
# _detect_requirements
# ===========================================================================


def test_detect_requirements_encontra_na_raiz(executor_module, coder_ws):
    (coder_ws / "requirements.txt").write_text("fastapi\nuvicorn")
    result = executor_module._detect_requirements(coder_ws)
    assert result == "requirements.txt"


def test_detect_requirements_encontra_em_subdir(executor_module, coder_ws):
    (coder_ws / "requirements").mkdir()
    (coder_ws / "requirements" / "base.txt").write_text("fastapi")
    result = executor_module._detect_requirements(coder_ws)
    assert result == "requirements/base.txt"


def test_detect_requirements_retorna_none_se_ausente(executor_module, coder_ws):
    result = executor_module._detect_requirements(coder_ws)
    assert result is None


# ===========================================================================
# _generate_dockerfile
# ===========================================================================


def test_generate_dockerfile_com_requirements(executor_module, coder_ws):
    """Dockerfile gerado deve conter COPY e pip install do requirements.txt."""
    (coder_ws / "requirements.txt").write_text("fastapi\nuvicorn[standard]")
    (coder_ws / "app").mkdir()
    (coder_ws / "app" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

    dockerfile = executor_module._generate_dockerfile(coder_ws)
    assert "COPY requirements.txt" in dockerfile
    assert "pip install" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert "uvicorn" in dockerfile
    assert "app.main:app" in dockerfile


def test_generate_dockerfile_sem_requirements_fallback(executor_module, coder_ws):
    """Sem requirements.txt, instala pacotes padrão inline."""
    (coder_ws / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

    dockerfile = executor_module._generate_dockerfile(coder_ws)
    assert "fastapi" in dockerfile
    assert "uvicorn" in dockerfile
    assert "jinja2" in dockerfile


def test_generate_dockerfile_com_pyproject(executor_module, coder_ws):
    """Com pyproject.toml, usa pip install . no Dockerfile."""
    (coder_ws / "pyproject.toml").write_text("[project]\nname='myapp'")
    (coder_ws / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

    dockerfile = executor_module._generate_dockerfile(coder_ws)
    assert "COPY pyproject.toml" in dockerfile
    assert "pip install" in dockerfile


# ===========================================================================
# tool_listar_arquivos_coder
# ===========================================================================


def test_listar_arquivos_coder_vazio(executor_module, coder_ws):
    """Workspace vazio retorna lista vazia."""
    result = executor_module.tool_listar_arquivos_coder()
    assert result["total"] == 0
    assert result["arquivos"] == []


def test_listar_arquivos_coder_com_arquivos(executor_module, coder_ws):
    """Lista arquivos recursivamente, excluindo __pycache__."""
    (coder_ws / "app").mkdir()
    (coder_ws / "app" / "main.py").write_text("# main")
    (coder_ws / "app" / "__pycache__").mkdir()
    (coder_ws / "app" / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"x")
    (coder_ws / "requirements.txt").write_text("fastapi")

    result = executor_module.tool_listar_arquivos_coder()
    assert result["total"] == 2
    assert "app/main.py" in result["arquivos"]
    assert "requirements.txt" in result["arquivos"]
    assert not any("__pycache__" in f for f in result["arquivos"])


# ===========================================================================
# tool_verificar_docker (mocked)
# ===========================================================================


def test_verificar_docker_disponivel(executor_module):
    """Retorna disponivel=True quando Docker está ok."""
    mock_client = MagicMock()
    mock_client.version.return_value = {"Version": "24.0.7"}

    with patch("docker.from_env", return_value=mock_client):
        result = executor_module.tool_verificar_docker()
    assert result["disponivel"] is True
    assert result["versao"] == "24.0.7"
    assert result["erro"] is None


def test_verificar_docker_indisponivel(executor_module):
    """Retorna disponivel=False quando Docker não acessível."""
    with patch("docker.from_env", side_effect=Exception("connection refused")):
        result = executor_module.tool_verificar_docker()
    assert result["disponivel"] is False
    assert "connection refused" in result["erro"]


# ===========================================================================
# tool_executar_em_docker — cenário de sucesso (mocked)
# ===========================================================================


def test_executar_em_docker_sem_python_no_workspace(executor_module, coder_ws, exec_ws, mock_tool_context):
    """Retorna erro se não há arquivos .py no workspace."""
    result = executor_module.tool_executar_em_docker(mock_tool_context)
    assert result["status"] == "erro"
    assert "Python" in result["mensagem"]
    assert mock_tool_context.state["_last_exec_status"] == "erro"


def test_executar_em_docker_falha_conexao_docker(executor_module, coder_ws, exec_ws, mock_tool_context):
    """Retorna erro se Docker daemon não está acessível."""
    (coder_ws / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

    with patch("docker.from_env", side_effect=Exception("Docker not running")):
        result = executor_module.tool_executar_em_docker(mock_tool_context)
    assert result["status"] == "erro"
    assert "Docker" in result["mensagem"]
    assert mock_tool_context.state["_last_exec_status"] == "erro"


def test_executar_em_docker_falha_build(executor_module, coder_ws, exec_ws, mock_tool_context):
    """Retorna falha_build quando docker build falha."""
    from docker.errors import BuildError

    (coder_ws / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    (coder_ws / "requirements.txt").write_text("fastapi\nuvicorn")

    mock_client = MagicMock()
    mock_client.images.build.side_effect = BuildError(
        reason="pip install failed", build_log=[]
    )
    mock_client.containers.get.side_effect = Exception("not found")

    with patch("docker.from_env", return_value=mock_client):
        result = executor_module.tool_executar_em_docker(mock_tool_context)
    assert result["status"] == "falha_build"
    assert "Falha" in result["mensagem"] or "falha" in result["mensagem"].lower()
    assert mock_tool_context.state["_last_exec_status"] == "falha_build"


def test_executar_em_docker_sucesso_completo(executor_module, coder_ws, exec_ws, mock_tool_context):
    """Fluxo completo de sucesso: build ok, container running, healthcheck ok, main route ok."""
    (coder_ws / "app").mkdir()
    (coder_ws / "app" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    (coder_ws / "requirements.txt").write_text("fastapi\nuvicorn[standard]")

    mock_client = MagicMock()
    mock_image = MagicMock()
    mock_client.images.build.return_value = (mock_image, iter([{"stream": "Step 1/5\n"}]))

    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.logs.return_value = b"INFO: Uvicorn running on 0.0.0.0:8000"
    mock_container.attrs = {
        "State": {"ExitCode": 0},
        "NetworkSettings": {"Ports": {"8000/tcp": [{"HostPort": "8000"}]}},
    }
    mock_client.containers.run.return_value = mock_container
    mock_client.containers.get.side_effect = Exception("not found")  # cleanup

    # Mock responses: /docs → 200, /openapi.json → schema com rota /, / → 200
    def mock_get(url, **kwargs):
        resp = MagicMock()
        if "/openapi.json" in url:
            resp.status_code = 200
            resp.json.return_value = {
                "paths": {
                    "/": {"get": {}},
                    "/docs": {"get": {}},
                    "/openapi.json": {"get": {}},
                }
            }
        else:
            resp.status_code = 200
        return resp

    with (
        patch("docker.from_env", return_value=mock_client),
        patch(
            "shared.tools.coding_review.docker_executor.time.sleep",
            return_value=None,
        ),
        patch("requests.get", side_effect=mock_get),
    ):
        result = executor_module.tool_executar_em_docker(mock_tool_context)

    assert result["status"] == "sucesso"
    assert "8000" in result["access_url"]
    assert result["container_name"] == "cr-executor-run"
    assert mock_tool_context.state["_last_exec_status"] == "sucesso"


def test_executar_em_docker_falha_rota_principal_500(executor_module, coder_ws, exec_ws, mock_tool_context):
    """Quando /docs OK mas rota principal retorna 500, deve reportar falha_runtime."""
    (coder_ws / "app").mkdir()
    (coder_ws / "app" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    (coder_ws / "requirements.txt").write_text("fastapi\nuvicorn[standard]")

    mock_client = MagicMock()
    mock_image = MagicMock()
    mock_client.images.build.return_value = (mock_image, iter([{"stream": "Step 1/5\n"}]))

    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.logs.return_value = b"ERROR: TemplateNotFoundError: register.html"
    mock_container.attrs = {"State": {"ExitCode": 0}}
    mock_client.containers.run.return_value = mock_container
    mock_client.containers.get.side_effect = Exception("not found")

    call_count = {"n": 0}

    def mock_get(url, **kwargs):
        call_count["n"] += 1
        resp = MagicMock()
        if "/docs" in url and "/openapi" not in url:
            resp.status_code = 200
        elif "/openapi.json" in url:
            resp.status_code = 200
            resp.json.return_value = {
                "paths": {
                    "/register": {"get": {}},
                    "/docs": {"get": {}},
                    "/openapi.json": {"get": {}},
                }
            }
        elif "/register" in url:
            resp.status_code = 500
            resp.text = '{"detail": "TemplateNotFoundError: register.html"}'
        else:
            resp.status_code = 200
        return resp

    with (
        patch("docker.from_env", return_value=mock_client),
        patch(
            "shared.tools.coding_review.docker_executor.time.sleep",
            return_value=None,
        ),
        patch("requests.get", side_effect=mock_get),
    ):
        result = executor_module.tool_executar_em_docker(mock_tool_context)

    assert result["status"] == "falha_runtime"
    assert "500" in result["mensagem"] or "TemplateNotFoundError" in result["mensagem"]
    assert mock_tool_context.state["_last_exec_status"] == "falha_runtime"


# ===========================================================================
# Integração: coder instruction contém {execution_result?}
# ===========================================================================


def test_coder_instruction_contem_execution_result_placeholder(tmp_path, monkeypatch):
    """O coder.instruction deve conter {execution_result?} para ADK state injection."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    # A instrução deve conter o placeholder para state injection
    assert "{execution_result?}" in instr, (
        "Placeholder {execution_result?} ausente na instrução do coder. "
        "O LoopAgent não conseguirá injetar logs de erro do executor."
    )


def test_coder_instruction_contem_modo_operacao(tmp_path, monkeypatch):
    """O coder.instruction deve conter a seção MODO DE OPERAÇÃO."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "MODO DE OPERAÇÃO" in instr
    assert "RESULTADO DA EXECUÇÃO ANTERIOR" in instr


def test_executor_output_key_matches_coder_placeholder(tmp_path, monkeypatch):
    """executor.output_key deve ser 'execution_result' (same key used in coder placeholder)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import cr_coder, cr_executor

    importlib.reload(cr_executor)
    importlib.reload(cr_coder)

    output_key = cr_executor.agent.output_key
    assert output_key == "execution_result"
    # Confirm the placeholder in coder matches
    assert f"{{{output_key}?}}" in cr_coder.agent.instruction


# ===========================================================================
# LoopAgent structure
# ===========================================================================


def test_loop_agent_max_iterations():
    """LoopAgent deve ter max_iterations=5."""
    from src.agents.workflow_coding_review.agent import _code_execute_loop

    assert _code_execute_loop.max_iterations == 5


def test_loop_agent_sub_agents_order():
    """LoopAgent deve ter coder ANTES de executor."""
    from src.agents.workflow_coding_review.agent import _code_execute_loop

    names = [sa.name for sa in _code_execute_loop.sub_agents]
    assert names[0] == "cr_coder_agent"
    assert names[1] == "cr_executor_agent"


# ===========================================================================
# _discover_main_route
# ===========================================================================


def test_discover_main_route_prioriza_raiz(executor_module):
    """Se /openapi.json tem '/' nas rotas, retorna '/'."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "paths": {
            "/": {"get": {}},
            "/users": {"get": {}},
            "/docs": {"get": {}},
            "/openapi.json": {"get": {}},
        }
    }

    mock_http = MagicMock()
    mock_http.get.return_value = mock_resp

    result = executor_module._discover_main_route("http://localhost:8000", mock_http)
    assert result == "/"


def test_discover_main_route_ignora_docs(executor_module):
    """Rotas internas (/docs, /openapi.json, /redoc) são filtradas."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "paths": {
            "/docs": {"get": {}},
            "/openapi.json": {"get": {}},
            "/redoc": {"get": {}},
            "/register": {"get": {}},
        }
    }

    mock_http = MagicMock()
    mock_http.get.return_value = mock_resp

    result = executor_module._discover_main_route("http://localhost:8000", mock_http)
    assert result == "/register"


def test_discover_main_route_sem_get_routes(executor_module):
    """Se app só tem POST routes, retorna None (API pura)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "paths": {
            "/docs": {"get": {}},
            "/openapi.json": {"get": {}},
            "/api/items": {"post": {}},
        }
    }

    mock_http = MagicMock()
    mock_http.get.return_value = mock_resp

    result = executor_module._discover_main_route("http://localhost:8000", mock_http)
    assert result is None


def test_discover_main_route_fallback_on_error(executor_module):
    """Se /openapi.json falhar, retorna '/' como fallback."""
    mock_http = MagicMock()
    mock_http.get.side_effect = Exception("connection error")

    result = executor_module._discover_main_route("http://localhost:8000", mock_http)
    assert result == "/"


# ===========================================================================
# Coder instruction: README requirement
# ===========================================================================


def test_coder_instruction_exige_readme(tmp_path, monkeypatch):
    """O coder.instruction deve exigir criação de README.md com URL de acesso."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "README.md" in instr
    assert "http://localhost:8000" in instr


# ===========================================================================
# Fixed port constant
# ===========================================================================


def test_host_port_is_fixed_8000(executor_module):
    """Porta do host deve ser fixa em 8000."""
    assert executor_module._HOST_PORT == 8000


# ===========================================================================
# Guarded exit_loop: tool_exit_loop_se_sucesso
# ===========================================================================


def test_exit_loop_bloqueado_quando_falha(executor_module, mock_tool_context):
    """tool_exit_loop_se_sucesso deve BLOQUEAR se status não é sucesso."""
    mock_tool_context.state["_last_exec_status"] = "falha_runtime"

    result = executor_module.tool_exit_loop_se_sucesso(mock_tool_context)
    assert result["encerrado"] is False
    assert "BLOQUEADO" in result["motivo"]
    # escalate NÃO deve ter sido setado para True
    assert mock_tool_context.actions.escalate is False


def test_exit_loop_bloqueado_sem_estado(executor_module, mock_tool_context):
    """tool_exit_loop_se_sucesso deve BLOQUEAR se nunca houve execução."""
    # state vazio — nenhuma execução ainda
    result = executor_module.tool_exit_loop_se_sucesso(mock_tool_context)
    assert result["encerrado"] is False
    assert "BLOQUEADO" in result["motivo"]


def test_exit_loop_permitido_quando_sucesso(executor_module, mock_tool_context):
    """tool_exit_loop_se_sucesso deve PERMITIR se status é sucesso."""
    mock_tool_context.state["_last_exec_status"] = "sucesso"

    result = executor_module.tool_exit_loop_se_sucesso(mock_tool_context)
    assert result["encerrado"] is True
    # escalate deve ter sido setado a True
    assert mock_tool_context.actions.escalate is True


def test_exit_loop_bloqueado_apos_falha_build(executor_module, mock_tool_context):
    """tool_exit_loop_se_sucesso bloqueado após falha_build."""
    mock_tool_context.state["_last_exec_status"] = "falha_build"

    result = executor_module.tool_exit_loop_se_sucesso(mock_tool_context)
    assert result["encerrado"] is False
    assert "falha_build" in result["motivo"]
