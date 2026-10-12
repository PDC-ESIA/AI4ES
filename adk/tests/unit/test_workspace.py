"""Tests para shared/workspace.py — workspace centralizado dos agentes."""

import os
from pathlib import Path

import pytest


def test_get_workspace_root_default(monkeypatch, tmp_path):
    """Sem env var, usa ./workspace_output relativo ao cwd."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WORKSPACE_OUTPUT_DIR", raising=False)
    from shared.workspace import get_workspace_root
    root = get_workspace_root()
    assert root == (tmp_path / "workspace_output").resolve()


def test_get_workspace_root_absoluto(monkeypatch, tmp_path):
    """Caminho absoluto é usado diretamente."""
    target = tmp_path / "custom_ws"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(target))
    from shared.workspace import get_workspace_root
    root = get_workspace_root()
    assert root == target.resolve()


def test_get_workspace_root_til_expandido(monkeypatch, tmp_path):
    """~ é expandido para home (usamos um fake HOME via tmp_path)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", "~/meu_ws")
    from shared.workspace import get_workspace_root
    root = get_workspace_root()
    assert root == (tmp_path / "meu_ws").resolve()


def test_init_workspace_cria_somente_raiz(monkeypatch, tmp_path):
    """init_workspace cria apenas a raiz + marker; subpastas são lazy."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import init_workspace, AGENT_DIRS
    root = init_workspace()
    assert root.is_dir()
    # Nenhuma subpasta de agente deve existir logo após init
    for subdir in set(AGENT_DIRS.values()):
        assert not (root / subdir).is_dir(), (
            f"Subpasta '{subdir}' não deveria existir antes de get_agent_workspace()"
        )


def test_get_agent_workspace_cria_subpasta_sob_demanda(monkeypatch, tmp_path):
    """get_agent_workspace() cria a subpasta na primeira chamada (lazy)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import init_workspace, get_agent_workspace, AGENT_DIRS
    root = init_workspace()
    # Antes: subpasta não existe
    agent = "context_engineer"
    subdir = AGENT_DIRS[agent]
    assert not (root / subdir).is_dir()
    # Depois: get_agent_workspace cria sob demanda
    path = get_agent_workspace(agent)
    assert path.is_dir()
    assert path == (root / subdir).resolve()


def test_init_workspace_nao_apaga_existente(monkeypatch, tmp_path):
    """init_workspace reaproveita o workspace existente — nada é apagado."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import init_workspace
    root = init_workspace()
    (root / "artefato.txt").write_text("dados anteriores")
    root = init_workspace()
    assert (root / "artefato.txt").read_text() == "dados anteriores"


def test_get_agent_workspace_agente_conhecido(monkeypatch, tmp_path):
    """Retorna path correto para agente mapeado em AGENT_DIRS."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace, AGENT_DIRS
    path = get_agent_workspace("context_engineer")
    assert path == (tmp_path / "ws" / AGENT_DIRS["context_engineer"]).resolve()


def test_get_agent_workspace_agente_desconhecido(monkeypatch, tmp_path):
    """Levanta ValueError para agente não mapeado."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace
    with pytest.raises(ValueError, match="não possui subpasta mapeada"):
        get_agent_workspace("agente_inexistente_xyz")


def test_agent_dirs_cobre_agentes_principais():
    """Smoke test: AGENT_DIRS tem entradas pros agentes principais dos 4 Times."""
    from shared.workspace import AGENT_DIRS
    esperados = [
        "requirements_agent", "context_engineer",
        "design_architect", "qa_agent",
        "coder_agent", "review_agent",
        "orchestrator",
    ]
    for agente in esperados:
        assert agente in AGENT_DIRS, f"Agente {agente} ausente em AGENT_DIRS"


def test_init_workspace_cria_marker(monkeypatch, tmp_path):
    """init_workspace cria o marker .ai4se_workspace na raiz."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import init_workspace, _WORKSPACE_MARKER
    root = init_workspace()
    marker = root / _WORKSPACE_MARKER
    assert marker.is_file()
    assert "AI4SE" in marker.read_text(encoding="utf-8")


def test_init_workspace_aceita_diretorio_existente_sem_marker(monkeypatch, tmp_path):
    """Diretório pré-existente sem marker é preservado e ganha o marker."""
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    (ws_dir / "arquivo_qualquer.txt").write_text("dados")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_dir))
    from shared.workspace import init_workspace, _WORKSPACE_MARKER
    root = init_workspace()
    assert (root / "arquivo_qualquer.txt").is_file()
    assert (root / _WORKSPACE_MARKER).is_file()


# ── Workspace por sessão ──────────────────────────────────────────────────

_SESSION_DIR_RE = r"^\d{8}-\d{4}-"


def _session_dir(base: Path, sid: str) -> Path:
    """Única pasta da sessão em base (nome <yyyyMMdd-HHmm>-<sid>)."""
    import re
    found = [d for d in base.iterdir() if re.match(_SESSION_DIR_RE + re.escape(sid) + "$", d.name)]
    assert len(found) == 1, f"esperada 1 pasta para {sid!r}, achou {found}"
    return found[0]


def test_sem_sessao_raiz_e_o_base(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_session_id, get_workspace_root
    assert get_session_id() is None
    assert get_workspace_root() == (tmp_path / "ws").resolve()


def test_session_workspace_cria_pasta_da_sessao(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import (
        _WORKSPACE_MARKER, get_agent_workspace, get_session_id,
        get_workspace_root, session_workspace,
    )
    with session_workspace("sess-1") as root:
        assert root == _session_dir((tmp_path / "ws").resolve(), "sess-1")
        assert get_workspace_root() == root
        assert (root / _WORKSPACE_MARKER).is_file()
        assert get_agent_workspace("cr_coder") == root / "coder" / "src"
    assert get_session_id() is None
    assert get_workspace_root() == (tmp_path / "ws").resolve()


def test_sessoes_nao_compartilham_arquivos(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_agent_workspace, session_workspace
    with session_workspace("a"):
        (get_agent_workspace("cr_coder") / "main.py").write_text("a")
    with session_workspace("b"):
        assert not (get_agent_workspace("cr_coder") / "main.py").exists()
    with session_workspace("a"):
        assert (get_agent_workspace("cr_coder") / "main.py").read_text() == "a"


def test_sessoes_concorrentes_isoladas_por_task(monkeypatch, tmp_path):
    """ContextVar: duas tasks asyncio simultâneas veem cada uma sua raiz."""
    import asyncio
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_workspace_root, session_workspace

    async def run(sid):
        with session_workspace(sid):
            await asyncio.sleep(0.01)  # força intercalação entre as tasks
            return get_workspace_root().name.split("-", 2)[2]

    async def main():
        return await asyncio.gather(run("x"), run("y"))

    assert asyncio.run(main()) == ["x", "y"]


@pytest.mark.parametrize("sid", ["", "..", "../fora", "a/b", ".oculto", "a b"])
def test_session_id_invalido_e_recusado(sid):
    from shared.workspace import set_session_id
    with pytest.raises(ValueError, match="session_id inválido"):
        set_session_id(sid)


def test_delete_session_workspace(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import delete_session_workspace, session_workspace
    with session_workspace("apagar"):
        pass
    with session_workspace("manter"):
        pass
    assert delete_session_workspace("apagar") is True
    assert not any(d.name.endswith("-apagar") for d in (tmp_path / "ws").iterdir())
    assert _session_dir(tmp_path / "ws", "manter").is_dir()
    assert delete_session_workspace("apagar") is False


def test_delete_session_workspace_recusa_sem_marker(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    alheio = tmp_path / "ws" / "20260101-0000-alheio"
    alheio.mkdir(parents=True)
    from shared.workspace import delete_session_workspace
    with pytest.raises(RuntimeError, match="não contém o marker"):
        delete_session_workspace("alheio")
    assert alheio.is_dir()


def test_tool_bound_resolve_workspace_da_sessao_na_chamada(monkeypatch, tmp_path):
    """Agente criado UMA vez escreve na pasta da sessão ativa a cada chamada."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.agent_factory import (
        _bind_tool_to_workspace, lazy_agent_workspace, lazy_workspace_root,
    )
    from shared.workspace import session_workspace

    def tool_criar_arquivo(nome: str, base_dir: str = "") -> str:
        destino = Path(base_dir) / nome
        destino.write_text("ok")
        return str(destino)

    tool = _bind_tool_to_workspace(
        tool_criar_arquivo, lazy_agent_workspace("cr_coder"), lazy_workspace_root()
    )
    for sid in ("s1", "s2"):
        with session_workspace(sid):
            caminho = Path(tool.func(nome="f.txt"))
        raiz = _session_dir((tmp_path / "ws").resolve(), sid)
        assert caminho == raiz / "coder" / "src" / "f.txt"


def test_plugin_define_sessao_externa_e_preserva_em_runner_aninhado(monkeypatch, tmp_path):
    import asyncio
    from types import SimpleNamespace
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import get_session_id
    from shared.workspace_plugin import SessionWorkspacePlugin

    plugin = SessionWorkspacePlugin()
    externo = SimpleNamespace(invocation_id="i1", session=SimpleNamespace(id="externa"))
    interno = SimpleNamespace(invocation_id="i2", session=SimpleNamespace(id="interna"))

    async def main():
        await plugin.before_run_callback(invocation_context=externo)
        assert get_session_id() == "externa"
        await plugin.before_run_callback(invocation_context=interno)
        assert get_session_id() == "externa"  # runner aninhado herda a externa
        await plugin.after_run_callback(invocation_context=interno)
        assert get_session_id() == "externa"
        await plugin.after_run_callback(invocation_context=externo)
        assert get_session_id() is None

    asyncio.run(main())
    assert _session_dir(tmp_path / "ws", "externa").is_dir()
    assert not any(d.name.endswith("-interna") for d in (tmp_path / "ws").iterdir())


def test_nome_da_pasta_tem_timestamp(monkeypatch, tmp_path):
    import re
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.workspace import session_workspace
    with session_workspace("abc-123") as root:
        assert re.fullmatch(r"\d{8}-\d{4}-abc-123", root.name)


def test_sessao_reaproveita_pasta_existente_com_timestamp_antigo(monkeypatch, tmp_path):
    """Nova execução (ou novo processo) da sessão acha a pasta já criada."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    existente = tmp_path / "ws" / "20250101-0930-sess-velha"
    existente.mkdir(parents=True)
    (existente / "artefato.txt").write_text("x")
    from shared.workspace import session_workspace
    with session_workspace("sess-velha") as root:
        assert root == existente.resolve()
        assert (root / "artefato.txt").is_file()


def test_session_id_nao_casa_com_sufixo_de_outra_sessao(monkeypatch, tmp_path):
    """'b' não pode reaproveitar a pasta de 'a-b' (glob ancorado no timestamp)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    (tmp_path / "ws" / "20250101-0930-a-b").mkdir(parents=True)
    from shared.workspace import session_workspace
    with session_workspace("b") as root:
        assert root.name != "20250101-0930-a-b"
        assert root.name.endswith("-b")
