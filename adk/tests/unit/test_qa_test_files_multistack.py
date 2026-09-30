"""Proteções e reexecução multistack do code_fix_agent."""

from pathlib import Path

import pytest

from shared.tools import qa_test_files


@pytest.mark.parametrize(
    ("relative_path", "original", "corrected", "language"),
    [
        (
            "coder/src/tests/unit/calculator.test.js",
            "test('old', () => {});\n",
            "test('new', () => {});\n",
            "javascript-typescript",
        ),
        (
            "coder/src/src/test/java/com/example/CalculatorTest.java",
            "class CalculatorTest { @Test void oldTest() {} }\n",
            "class CalculatorTest { @Test void newTest() {} }\n",
            "java",
        ),
        (
            "coder/src/calculator_test.go",
            "package calculator\nfunc TestOld(t *testing.T) {}\n",
            "package calculator\nfunc TestNew(t *testing.T) {}\n",
            "go",
        ),
        (
            "coder/src/calculator_test.generated.go",
            "package calculator\nfunc TestOld(t *testing.T) {}\n",
            "package calculator\nfunc TestNew(t *testing.T) {}\n",
            "go",
        ),
    ],
)
def test_code_fix_le_e_altera_testes_multistack(
    tmp_path,
    monkeypatch,
    relative_path,
    original,
    corrected,
    language,
):
    workspace = tmp_path / "workspace"
    test_file = workspace / relative_path
    test_file.parent.mkdir(parents=True)
    test_file.write_text(original, encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    before = qa_test_files.read_qa_test(str(test_file))
    result = qa_test_files.write_qa_test(str(test_file), corrected)

    assert before["status"] == "ok"
    assert before["linguagem"] == language
    assert result["status"] == "aplicado"
    assert result["linguagem"] == language
    assert test_file.read_text(encoding="utf-8") == corrected


@pytest.mark.parametrize(
    "relative_path",
    [
        "coder/src/src/calculator.js",
        "coder/src/src/main/java/com/example/Calculator.java",
        "coder/src/calculator.go",
    ],
)
def test_code_fix_rejeita_codigo_de_producao(tmp_path, monkeypatch, relative_path):
    workspace = tmp_path / "workspace"
    production = workspace / relative_path
    production.parent.mkdir(parents=True)
    production.write_text("production\n", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    result = qa_test_files.write_qa_test(str(production), "test('x', () => {});\n")

    assert result["status"] == "erro"
    assert "Somente arquivos de teste gerenciados" in result["erro"]
    assert production.read_text(encoding="utf-8") == "production\n"


def test_code_fix_reexecuta_node_pelo_perfil_detectado(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    project = workspace / "coder" / "src"
    test_file = project / "tests" / "unit" / "calculator.test.js"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("test('ok', () => {});\n", encoding="utf-8")
    (project / "package.json").write_text(
        '{"type":"commonjs","scripts":{"test":"node --test"}}\n',
        encoding="utf-8",
    )
    (project / "calculator.js").write_text("module.exports = {};\n", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    captured = {}

    def execute(profile_id: str, project_root: Path, path: Path):
        captured.update(
            profile_id=profile_id,
            project_root=project_root,
            path=path,
        )
        return {"status": "sucesso", "perfil": profile_id, "erros": []}

    monkeypatch.setattr(qa_test_files, "executar_teste_unitario", execute)

    result = qa_test_files.executar_teste_unitario_corrigido(
        str(test_file), "node-node-test"
    )

    assert result["status"] == "sucesso"
    assert result["arquivo"] == str(test_file.resolve())
    assert captured == {
        "profile_id": "node-node-test",
        "project_root": project.resolve(),
        "path": test_file.resolve(),
    }


def test_code_fix_expoe_reexecucao_multistack():
    from src.agents.qa_agent.subagents.code_fix_agent.agent import agent

    tools = {tool.name for tool in agent.tools}

    assert "read_qa_test" in tools
    assert "write_qa_test" in tools
    assert "executar_teste_unitario_corrigido" in tools


@pytest.mark.parametrize(("relative_path", "content"), [
    ("coder/src/tests/unit/secret.test.js", 'test("x", () => { const api_key = "sk-real-Abc123xyz"; });'),
    ("coder/src/src/test/java/SecretTest.java", 'class SecretTest { @Test void x() { String api_key = "sk-real-Abc123xyz"; } }'),
    ("coder/src/secret_test.go", 'package app\nfunc TestX(t *testing.T) { api_key = "sk-real-Abc123xyz" }'),
    ("coder/src/tests/unit/env.test.js", 'test("x", () => { const value = process.env.GOOGLE_API_KEY; });'),
])
def test_multistack_preserva_guardrails_antes_de_escrever(tmp_path, monkeypatch, relative_path, content):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True)
    path.write_text("original", encoding="utf-8")
    result = qa_test_files.write_qa_test(str(path), content)
    assert result["status"] == "erro"
    assert "risco de segurança" in result["erro"]
    assert "sk-real-Abc123xyz" not in result["erro"]
    assert path.read_text(encoding="utf-8") == "original"
