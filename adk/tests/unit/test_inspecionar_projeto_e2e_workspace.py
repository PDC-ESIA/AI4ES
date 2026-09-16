"""Contenção de `workspace_projeto` no E2E (P5 dos guard rails do QA).

Antes desta mudança, `_resolver_workspace` aceitava qualquer caminho dentro
de `_RAIZ_ADK` (o repositório inteiro do ADK) ou de `get_workspace_root()`
(workspace_output/, que incluía `adk_debug.yaml` — prompt e resposta
completos de todos os agentes quando ADK_LOG_PLUGIN=file). Nenhuma das duas
tinha caso de uso documentado ou testado. Agora só `get_workspace_root()` é
aceito. Além disso, o default de `ADK_DEBUG_LOG_PATH` foi movido para fora
de workspace_output/ (ver shared/observability.py:_DEBUG_LOG_PADRAO) — o
arquivo de debug log continua excluído explicitamente da varredura como
defesa extra, para o caso de alguém configurar ADK_DEBUG_LOG_PATH de volta
para dentro do workspace gerenciado.
"""

from shared.workspace import get_workspace_root
from src.agents.qa_agent.subagents.e2e_test_generator.tools.inspecionar_projeto_e2e import (
    _RAIZ_ADK,
    _arquivos_do_workspace,
    _caminho_debug_log_excluido,
    _resolver_workspace,
)


def test_resolver_workspace_rejeita_shared_do_proprio_adk(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    raiz, erro = _resolver_workspace("shared")

    assert raiz is None
    assert erro is not None


def test_resolver_workspace_rejeita_src_do_proprio_adk(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    raiz, erro = _resolver_workspace("src")

    assert raiz is None
    assert erro is not None


def test_resolver_workspace_rejeita_caminho_absoluto_para_shared(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    raiz, erro = _resolver_workspace(str(_RAIZ_ADK / "shared"))

    assert raiz is None
    assert erro is not None


def test_resolver_workspace_aceita_diretorio_dentro_do_workspace_gerenciado(
    monkeypatch, tmp_path
):
    workspace = tmp_path / "workspace_output"
    alvo = workspace / "coder" / "src"
    alvo.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    raiz, erro = _resolver_workspace(str(alvo))

    assert erro is None
    assert raiz == alvo.resolve()


def test_debug_log_default_fica_fora_do_workspace_gerenciado(monkeypatch, tmp_path):
    """Sem ADK_DEBUG_LOG_PATH customizado, o default nem cai dentro da única
    raiz que _resolver_workspace aceita hoje — a exclusão explícita em
    _arquivos_do_workspace é defesa extra, não a única barreira."""
    monkeypatch.delenv("ADK_DEBUG_LOG_PATH", raising=False)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    debug_log = _caminho_debug_log_excluido()
    workspace_root = get_workspace_root().resolve()

    assert debug_log == (_RAIZ_ADK / "logs" / "adk_debug.yaml").resolve()
    assert not debug_log.is_relative_to(workspace_root)


def test_arquivos_do_workspace_nao_le_debug_log_se_alguem_reintroduzir_dentro(
    monkeypatch, tmp_path
):
    """Ainda que o default esteja fora, a exclusão explícita segue funcionando
    se ADK_DEBUG_LOG_PATH voltar a apontar para dentro de workspace_output/
    (defesa extra, não dependente de onde o default mora). Aponta para
    workspace/coder — a única raiz aceita hoje além do próprio E2E."""
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace_output"
    coder_dir = workspace / "coder"
    coder_dir.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", "workspace_output")
    monkeypatch.setenv("ADK_DEBUG_LOG_PATH", "workspace_output/adk_debug.yaml")

    (workspace / "adk_debug.yaml").write_text(
        "prompt: 'SEGREDO_QUE_NAO_PODE_VAZAR api_key=sk-real-123'\n",
        encoding="utf-8",
    )
    (coder_dir / "outro.yaml").write_text("chave: valor\n", encoding="utf-8")

    arquivos, _limites, bloqueios = _arquivos_do_workspace(str(coder_dir))

    assert not bloqueios
    nomes = {a.nome for a in arquivos}
    assert "adk_debug.yaml" not in nomes
    assert "outro.yaml" in nomes
    assert all("SEGREDO_QUE_NAO_PODE_VAZAR" not in a.conteudo for a in arquivos)


def test_arquivos_do_workspace_nao_le_debug_log_customizado(monkeypatch, tmp_path):
    """O mesmo vale quando ADK_DEBUG_LOG_PATH aponta para um caminho
    customizado dentro da raiz permitida (coder/)."""
    workspace = tmp_path / "workspace_output"
    coder_dir = workspace / "coder"
    coder_dir.mkdir(parents=True)
    log_customizado = coder_dir / "logs" / "meu_debug.yaml"
    log_customizado.parent.mkdir(parents=True)
    log_customizado.write_text(
        "prompt: 'OUTRO_SEGREDO token=ghp_real'\n", encoding="utf-8"
    )
    (coder_dir / "outro.yaml").write_text("chave: valor\n", encoding="utf-8")

    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    monkeypatch.setenv("ADK_DEBUG_LOG_PATH", str(log_customizado))

    arquivos, _limites, bloqueios = _arquivos_do_workspace(str(coder_dir))

    assert not bloqueios
    nomes = {a.nome for a in arquivos}
    assert "logs/meu_debug.yaml" not in nomes
    assert "outro.yaml" in nomes
    assert all("OUTRO_SEGREDO" not in a.conteudo for a in arquivos)


# ---------------------------------------------------------------------------
# P6.6 — allowlist explícita (_ROOTS_PERMITIDOS_E2E): Coder e o próprio E2E
# são aceitos; requirements/design (documentos, não a aplicação) rejeitados.
# ---------------------------------------------------------------------------


def test_resolver_workspace_aceita_workspace_do_coder(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    from shared.workspace import get_agent_workspace

    alvo = get_agent_workspace("coder")

    raiz, erro = _resolver_workspace(str(alvo))

    assert erro is None
    assert raiz == alvo.resolve()


def test_resolver_workspace_aceita_workspace_do_proprio_e2e(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    from shared.workspace import get_agent_workspace

    alvo = get_agent_workspace("e2e_test_generator")

    raiz, erro = _resolver_workspace(str(alvo))

    assert erro is None
    assert raiz == alvo.resolve()


def test_resolver_workspace_rejeita_requirements(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    from shared.workspace import get_agent_workspace

    alvo = get_agent_workspace("requirements")

    raiz, erro = _resolver_workspace(str(alvo))

    assert raiz is None
    assert erro is not None
    assert "documentos" in erro


def test_resolver_workspace_rejeita_design(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace_output"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    from shared.workspace import get_agent_workspace

    alvo = get_agent_workspace("design_architect")

    raiz, erro = _resolver_workspace(str(alvo))

    assert raiz is None
    assert erro is not None


def test_resolver_workspace_aceita_caminho_relativo_workspace_output_coder(
    monkeypatch, tmp_path
):
    """workspace_projeto='workspace_output/coder' (relativo, ancorado em
    _RAIZ_ADK) deve resolver para a mesma raiz que get_agent_workspace('coder')
    quando WORKSPACE_OUTPUT_DIR não está customizado para fora de _RAIZ_ADK.

    Isola completamente em tmp_path: chdir para tmp_path (não para o
    repositório real) e monkeypatcha _RAIZ_ADK do próprio módulo para
    tmp_path, para que tanto a âncora do caminho relativo quanto o default
    de WORKSPACE_OUTPUT_DIR (resolvido contra Path.cwd()) apontem para o
    mesmo lugar isolado — sem criar nada fora de tmp_path.
    """
    import sys

    import src.agents.qa_agent.subagents.e2e_test_generator.tools.inspecionar_projeto_e2e  # noqa: F401

    modulo = sys.modules[
        "src.agents.qa_agent.subagents.e2e_test_generator.tools.inspecionar_projeto_e2e"
    ]

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WORKSPACE_OUTPUT_DIR", raising=False)
    monkeypatch.setattr(modulo, "_RAIZ_ADK", tmp_path)

    from shared.workspace import get_agent_workspace

    alvo_esperado = get_agent_workspace("coder")
    raiz, erro = modulo._resolver_workspace("workspace_output/coder")

    assert erro is None
    assert raiz == alvo_esperado.resolve()


# ---------------------------------------------------------------------------
# P6.6 — redigir_segredos aplicado ao conteúdo lido antes de devolver ao LLM.
# ---------------------------------------------------------------------------


def test_arquivos_do_workspace_redige_credencial_em_yaml_do_coder(monkeypatch, tmp_path):
    """Arquivo .yaml de config do Coder com api_key não pode vazar a chave
    real para o LLM através do resultado da inspeção de projeto."""
    workspace = tmp_path / "workspace_output"
    coder_dir = workspace / "coder"
    coder_dir.mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    (coder_dir / "config.yaml").write_text(
        'api_key: "sk-real-vazando-123"\nnome_servico: catalogo\n',
        encoding="utf-8",
    )

    arquivos, _limites, bloqueios = _arquivos_do_workspace(str(coder_dir))

    assert not bloqueios
    config = next(a for a in arquivos if a.nome == "config.yaml")
    assert "sk-real-vazando-123" not in config.conteudo
    assert "[REDACTED]" in config.conteudo
    assert "nome_servico: catalogo" in config.conteudo
