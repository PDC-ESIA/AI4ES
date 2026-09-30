"""Fronteiras do sandbox: rejeição, configuração e conteúdo exportável."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from shared import qa_sandbox as sandbox


def fake_docker(monkeypatch, *, result=None, wait_error=None):
    import docker
    container = Mock()
    container.logs.return_value = json.dumps(result or {
        "exit_code": 0, "passed": 1, "failed": 0, "skipped": 0,
        "stdout": "PROMPT PRIVADO E CÓDIGO INTERNO", "covered_lines": 1,
        "num_statements": 1,
    }).encode()
    if wait_error:
        container.wait.side_effect = wait_error
    cliente = Mock()
    cliente.images.get.return_value.id = "sha256:trusted"
    cliente.containers.create.return_value = container
    monkeypatch.setattr(docker, "from_env", lambda **_: cliente)
    return cliente, container


def suite(tmp_path):
    origem = tmp_path / "suite"
    origem.mkdir()
    (origem / "test_ok.py").write_text("def test_ok(): assert True\n")
    return origem


def test_sandbox_nao_exporta_texto_e_isola_host(monkeypatch, tmp_path):
    cliente, container = fake_docker(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "segredo-do-host")
    resultado = sandbox.executar_isolado(suite(tmp_path), "test_ok.py")
    opcoes = cliente.containers.create.call_args.kwargs
    assert opcoes["network_mode"] == "none"
    assert opcoes["read_only"] is True
    assert opcoes["user"] == "1000:1000"
    assert opcoes["cap_drop"] == ["ALL"]
    assert opcoes["security_opt"] == ["no-new-privileges:true"]
    assert opcoes["pids_limit"] == 128
    assert opcoes["mem_limit"] == "1g"
    assert "GOOGLE_API_KEY" not in opcoes["environment"]
    assert len(opcoes["volumes"]) == 1
    caminho, montagem = next(iter(opcoes["volumes"].items()))
    assert montagem == {"bind": "/input", "mode": "ro"}
    assert not Path(caminho).exists()
    assert "stdout" not in resultado
    assert "PRIVADO" not in json.dumps(resultado)
    container.remove.assert_called_once_with(force=True, v=True)
    cliente.close.assert_called_once()


def test_sandbox_remove_container_em_timeout(monkeypatch, tmp_path):
    _, container = fake_docker(monkeypatch, wait_error=RuntimeError("token=segredo"))
    with pytest.raises(sandbox.SandboxIndisponivel) as erro:
        sandbox.executar_isolado(suite(tmp_path), "test_ok.py")
    assert "segredo" not in str(erro.value)
    container.remove.assert_called_once_with(force=True, v=True)


def test_sandbox_sem_imagem_nao_puxa_nem_executa(monkeypatch, tmp_path):
    cliente, _ = fake_docker(monkeypatch)
    cliente.images.get.side_effect = RuntimeError("imagem ausente")
    with pytest.raises(sandbox.SandboxIndisponivel):
        sandbox.executar_isolado(suite(tmp_path), "test_ok.py")
    cliente.images.pull.assert_not_called()
    cliente.containers.create.assert_not_called()


def test_snapshot_exclui_credenciais_e_prompts(tmp_path):
    origem = suite(tmp_path)
    for nome in (".env", "credentials.json", "prompt.py", "key.pem", "report.json"):
        (origem / nome).write_text("PRIVADO")
    (origem / "prompts").mkdir()
    (origem / "prompts" / "interno.txt").write_text("PRIVADO")
    destino = tmp_path / "snapshot"
    sandbox.copiar_entrada(origem, destino)
    assert [p.name for p in destino.rglob("*") if p.is_file()] == ["test_ok.py"]


def test_snapshot_rejeita_arquivo_grande(tmp_path):
    origem = suite(tmp_path)
    (origem / "grande.txt").write_bytes(b"x" * 2_000_001)
    with pytest.raises(ValueError, match="limite"):
        sandbox.copiar_entrada(origem, tmp_path / "snapshot")


def test_snapshot_rejeita_links(monkeypatch, tmp_path):
    origem = suite(tmp_path)
    # Independente da permissão de criar symlinks no Windows.
    real = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p.name == "test_ok.py" or real(p))
    with pytest.raises(ValueError, match="Links"):
        sandbox.copiar_entrada(origem, tmp_path / "snapshot")


@pytest.mark.parametrize("exit_code", [None, "0", False, -1])
def test_resultado_invalido_nao_vira_sucesso(monkeypatch, tmp_path, exit_code):
    fake_docker(monkeypatch, result={"exit_code": exit_code, "passed": 1})
    assert sandbox.executar_isolado(suite(tmp_path), "test_ok.py")["exit_code"] != 0


def test_runner_sem_sandbox_nao_faz_fallback(monkeypatch, tmp_path):
    from shared.tools import pytest_runner
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))
    pasta = tmp_path / "tests" / "inputs" / "caso"
    pasta.mkdir(parents=True)
    (pasta / "test_ok.py").write_text("def test_ok(): assert True")
    monkeypatch.setattr(pytest_runner, "executar_isolado", Mock(side_effect=sandbox.SandboxIndisponivel()))
    host = Mock(side_effect=AssertionError("não executar no host"))
    monkeypatch.setattr(pytest_runner.subprocess, "run", host)
    resultado = pytest_runner.executar_pytest_tool(str(pasta / "test_ok.py"))
    assert resultado["erros"][0]["codigo"] == "ERR_SANDBOX_INDISPONIVEL"
    host.assert_not_called()


def test_e2e_nao_inicia_processo_no_host(monkeypatch, tmp_path):
    import subprocess
    from src.agents.qa_agent.subagents.e2e_test_generator.tools import gerenciar_runtime_alvo as runtime
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))
    projeto = tmp_path / "coder"
    projeto.mkdir()
    host = Mock(side_effect=AssertionError("não executar no host"))
    monkeypatch.setattr(subprocess, "Popen", host)
    resultado = runtime.iniciar_runtime_alvo(SimpleNamespace(),
        SimpleNamespace(perfil_inicializacao="uvicorn", entrypoint="main:app"), str(projeto))
    assert resultado.status == "pronto"
    assert resultado.base_url == "http://127.0.0.1:8765"
    host.assert_not_called()


def test_diagnosticos_nao_publicam_prompt_ou_codigo(tmp_path, monkeypatch):
    from shared.tools import doubt_artifact, doubt_tool, build_fix_prompt
    privado = "PROMPT_INTERNO_SEM_CREDENCIAIS def algoritmo_privado(): return 42"
    monkeypatch.setattr(doubt_artifact, "_resolve_doubt_dir", lambda: tmp_path)
    monkeypatch.setattr(doubt_tool, "_resolve_doubt_dir", lambda: tmp_path)
    doubt_artifact.gerar_doubt_artifact(privado, suspect_code_or_prompt=privado,
                                      system_raw_response=privado, artifact_id=privado)
    doubt_tool.DoubtArtifactGenerator.generate(privado, privado, privado)
    for arquivo in tmp_path.glob("*.md"):
        assert privado not in arquivo.read_text(encoding="utf-8")
        assert "algoritmo_privado" not in arquivo.name
    prompt = build_fix_prompt.build_fix_prompt(privado, privado, privado, privado, privado)
    assert privado not in prompt
    resultado = build_fix_prompt.build_fix_prompt_from_error(privado, language=privado)
    assert privado not in json.dumps(resultado)


@pytest.mark.parametrize("passou,esperado", [(1, "aprovado"), (0, "falhou")])
def test_e2e_usa_sandbox_e_nao_aprova_suite_vazia(monkeypatch, tmp_path, passou, esperado):
    import importlib
    modulo = importlib.import_module(
        "src.agents.qa_agent.subagents.e2e_test_generator.tools.executar_playwright")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))
    destino = modulo.get_agent_workspace("e2e_test_generator")
    destino.mkdir(parents=True, exist_ok=True)
    projeto = modulo.get_agent_workspace("coder")
    projeto.mkdir(parents=True, exist_ok=True)
    spec = destino / "test.spec.ts"
    spec.write_text("import { test } from '@playwright/test';")
    executor = Mock(return_value={"passed": passou, "failed": 0, "skipped": 0, "exit_code": 0})
    monkeypatch.setattr(modulo, "executar_isolado", executor)
    entrada = SimpleNamespace(comando_execucao="playwright test")
    runtime = SimpleNamespace(workspace=str(projeto), comando=["uvicorn", "main:app"])
    resultado = modulo.executar_playwright(entrada, str(spec), runtime)
    assert resultado.status == esperado
    assert executor.call_args.kwargs["projeto"] == projeto.resolve()
    assert executor.call_args.kwargs["modo"] == "playwright"


def test_inspecao_nao_le_prompt_privado(monkeypatch, tmp_path):
    from src.agents.qa_agent.subagents.e2e_test_generator.tools.inspecionar_projeto_e2e import _arquivos_do_workspace
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))
    projeto = tmp_path / "coder"
    projeto.mkdir()
    (projeto / "prompt.py").write_text("PROMPT PRIVADO")
    (projeto / "main.py").write_text("VALUE = 42")
    arquivos, _, _ = _arquivos_do_workspace(str(projeto))
    assert [arquivo.nome for arquivo in arquivos] == ["main.py"]


@pytest.mark.parametrize("codigo", [
    "import os\nf = os.getenv\nf('KEY')",
    "import subprocess\nf = subprocess.run\nf(['ls'])",
    "import os\nx = dict(os.environ)",
])
def test_aliases_e_ambiente_completo_rejeitados(codigo):
    from shared.security import detectar_riscos_codigo
    assert detectar_riscos_codigo(codigo)
