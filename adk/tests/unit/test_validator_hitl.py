"""Testes do registro de aguardar_decisao_validacao no agente validator
(Time 2 / Design).

Mesmo padrão de adk/tests/unit/test_workflow_qa_hitl.py.
"""

from google.adk.tools import LongRunningFunctionTool


def test_validator_registra_aguardar_decisao_validacao_como_longrunning():
    """A tool DEVE ser LongRunningFunctionTool, não FunctionTool comum."""
    from src.agents.validator.agent import agent

    long_running_tools = [
        t for t in agent.tools if isinstance(t, LongRunningFunctionTool)
    ]
    assert len(long_running_tools) == 1, (
        f"Esperado exatamente 1 LongRunningFunctionTool. "
        f"Encontradas: {[type(t).__name__ for t in agent.tools]}"
    )

    decl = long_running_tools[0]._get_declaration()
    assert decl.name == "aguardar_decisao_validacao", (
        f"Nome inesperado: {decl.name}"
    )


def test_validator_instruction_nao_pausa_por_falha_de_validacao():
    """Sintaxe persistente vira REPROVADO sem pausa; a tool segue registrada."""
    from src.agents.validator.agent import agent

    assert "2 tentativas" in agent.instruction
    assert "aguardar_decisao_validacao) NÃO é acionada" in agent.instruction
    assert "CHAME\n    OBRIGATORIAMENTE a tool `aguardar_decisao_validacao`" not in agent.instruction

def test_validator_aguardar_decisao_validacao_schema_nao_quebra_gemini():
    """O FunctionDeclaration não pode ter any_of (Gemini 400 INVALID_ARGUMENT)."""
    from src.agents.validator.agent import agent

    long_running_tools = [
        t for t in agent.tools if isinstance(t, LongRunningFunctionTool)
    ]
    decl_json = long_running_tools[0]._get_declaration().model_dump_json(
        exclude_none=True, by_alias=True
    )
    assert "any_of" not in decl_json, (
        f"Schema contém any_of (Gemini API rejeita): {decl_json}"
    )


def test_validator_nao_aciona_markdown_specialist():
    from src.agents.validator.agent import agent
    nomes = [getattr(t, "name", "") for t in agent.tools]
    assert "markdown_specialist" not in nomes


def test_validator_grava_veredicto_e_manifesto_chega_a_ok(tmp_path, monkeypatch):
    """O formato do PASSO 5 do validator é lido como "pass" pelo manifesto."""
    from shared.tools import design_filesystem as df
    from src.agents.workflow_design_pipeline.manifest import _validation_verdict

    root = tmp_path / "design"
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    monkeypatch.setattr(df, "DESIGN_DIR", root)
    monkeypatch.setattr(df, "LOCKS_DIR", root / ".locks")

    nome = "VALIDATION/veredicto_diagramas.md"
    aprovado = ("# Veredicto de validação — diagramas\nResultado: APROVADO\nArquivos:\n"
                "- diagrama_HU-001_x.mmd: APROVADO\n")
    assert df.acquire_lock(nome, caller="validator")["status"] == "ok"
    assert df.save_artifact(nome, aprovado, caller="validator")["status"] == "ok"
    assert (root / "validation" / "veredicto_diagramas.md").exists()
    assert _validation_verdict(root) == "pass"
    # o markdown_specialist lê o veredicto pelo mesmo alias
    assert df.read_file(nome)["status"] == "ok"

    # Regravação com reprovação: o backup da versão anterior é ignorado.
    reprovado = aprovado.replace("Resultado: APROVADO", "Resultado: REPROVADO")
    assert df.save_artifact(nome, reprovado, caller="validator")["status"] == "ok"
    assert df.release_lock(nome, caller="validator")["status"] == "ok"
    assert _validation_verdict(root) == "fail"


def test_veredicto_com_aviso_conta_como_aprovado(tmp_path):
    """Falha só semântica vira "APROVADO COM AVISO" e não derruba o manifesto."""
    from src.agents.workflow_design_pipeline.manifest import _validation_verdict
    root = tmp_path / "design"
    (root / "validation").mkdir(parents=True)
    (root / "validation" / "veredicto_diagramas.md").write_text(
        "# Veredicto de validação — diagramas\nResultado: APROVADO\nArquivos:\n"
        "- diagrama_HU-001_x.mmd: APROVADO COM AVISO (componente X ausente)\n",
        encoding="utf-8",
    )
    assert _validation_verdict(root) == "pass"
