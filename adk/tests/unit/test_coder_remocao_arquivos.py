"""Remoção de arquivos e pastas pelo coder (issue #388).

Cobre `tool_remover_arquivo` — a capacidade que faltava ao coder do
`workflow_coding_review` para tratar renomeação, módulo descontinuado e arquivo
criado por engano em iteração anterior.

⚠️ Estes testes NÃO ficam em `test_filesystem_tools.py`: aquele arquivo está em
`collect_ignore` no `tests/unit/conftest.py` e não é executado pela suíte.

A auditoria por task (`auditar_remocao`) é coberta em
`test_coder_workspace_guard.py`, junto do resto do guard do coder.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shared.tools.coding_tools.filesystem_coding import tool_remover_arquivo

_LOGGER_DA_TOOL = "shared.tools.coding_tools.filesystem_coding"


@pytest.fixture
def workspace(tmp_path):
    """Workspace do coder, como a factory o injeta via base_dir."""
    ws = tmp_path / "coder" / "src"
    ws.mkdir(parents=True)
    return ws


@pytest.fixture
def cwd_isolado(tmp_path, monkeypatch):
    """CWD temporário, para o caminho legado (sem base_dir)."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestRemocaoBemSucedida:
    def test_remove_arquivo_existente(self, workspace):
        """Critério 1: após a operação, o arquivo não existe mais no disco."""
        alvo = workspace / "obsoleto.py"
        alvo.write_text("# módulo descontinuado\n", encoding="utf-8")

        result = tool_remover_arquivo("obsoleto.py", base_dir=str(workspace))

        assert result["sucesso"] is True
        assert result["tipo"] == "arquivo"
        assert result["codigo"] is None
        assert result["erro"] is None
        assert not alvo.exists()

    def test_remove_arquivo_em_subpasta_preservando_a_pasta(self, workspace):
        alvo = workspace / "app" / "legado.py"
        alvo.parent.mkdir()
        alvo.write_text("pass\n", encoding="utf-8")

        result = tool_remover_arquivo("app/legado.py", base_dir=str(workspace))

        assert result["sucesso"] is True
        assert not alvo.exists()
        assert alvo.parent.exists(), "só o arquivo sai; a pasta permanece"

    def test_remove_pasta_vazia(self, workspace):
        """Critério 5: remoção de pasta vazia é suportada."""
        vazia = workspace / "descontinuado"
        vazia.mkdir()

        result = tool_remover_arquivo("descontinuado", base_dir=str(workspace))

        assert result["sucesso"] is True
        assert result["tipo"] == "diretorio"
        assert not vazia.exists()

    def test_renomeacao_remove_o_antigo_e_preserva_o_novo(self, workspace):
        """O caso de uso da issue: arquivo movido/renomeado."""
        (workspace / "servico_antigo.py").write_text("x = 1\n", encoding="utf-8")
        (workspace / "servico_novo.py").write_text("x = 1\n", encoding="utf-8")

        result = tool_remover_arquivo("servico_antigo.py", base_dir=str(workspace))

        assert result["sucesso"] is True
        assert not (workspace / "servico_antigo.py").exists()
        assert (workspace / "servico_novo.py").exists()

    def test_remove_extensao_fora_da_whitelist_de_escrita(self, workspace):
        """Limpar o workspace não depende da whitelist de criação."""
        alvo = workspace / "sobra.log"
        alvo.write_text("ruído\n", encoding="utf-8")

        result = tool_remover_arquivo("sobra.log", base_dir=str(workspace))

        assert result["sucesso"] is True
        assert not alvo.exists()

    def test_sem_base_dir_resolve_do_cwd(self, cwd_isolado):
        """Comportamento legado, como nas demais tools do módulo."""
        Path("solto.txt").write_text("x", encoding="utf-8")

        result = tool_remover_arquivo("solto.txt")

        assert result["sucesso"] is True
        assert not Path("solto.txt").exists()

    def test_retorna_as_chaves_do_contrato(self, workspace):
        (workspace / "a.py").write_text("", encoding="utf-8")

        result = tool_remover_arquivo("a.py", base_dir=str(workspace))

        assert {"sucesso", "caminho", "tipo", "codigo", "erro"}.issubset(result)


class TestFalhasControladas:
    def test_caminho_inexistente_falha_sem_excecao(self, workspace):
        """Critério 2: falha controlada e explicativa, sem derrubar o pipeline."""
        result = tool_remover_arquivo("nao_existe.py", base_dir=str(workspace))

        assert result["sucesso"] is False
        assert result["codigo"] == "CAMINHO_INEXISTENTE"
        assert "não existe" in result["erro"]

    def test_pasta_nao_vazia_e_rejeitada_e_preservada(self, workspace):
        """Critério 5: comportamento definido — rejeita, e diz o que há dentro."""
        pasta = workspace / "app"
        pasta.mkdir()
        (pasta / "main.py").write_text("pass\n", encoding="utf-8")

        result = tool_remover_arquivo("app", base_dir=str(workspace))

        assert result["sucesso"] is False
        assert result["codigo"] == "DIRETORIO_NAO_VAZIO"
        assert "main.py" in result["erro"]
        assert (pasta / "main.py").exists(), "nada pode ser apagado em silêncio"

    def test_pasta_esvaziada_passa_a_ser_removivel(self, workspace):
        """O caminho de saída indicado na mensagem funciona de fato."""
        pasta = workspace / "app"
        pasta.mkdir()
        (pasta / "main.py").write_text("pass\n", encoding="utf-8")

        assert tool_remover_arquivo("app/main.py", base_dir=str(workspace))["sucesso"]
        assert tool_remover_arquivo("app", base_dir=str(workspace))["sucesso"]
        assert not pasta.exists()

    @pytest.mark.parametrize("caminho", ["", "   "])
    def test_caminho_vazio_falha(self, workspace, caminho):
        result = tool_remover_arquivo(caminho, base_dir=str(workspace))

        assert result["sucesso"] is False
        assert result["codigo"] == "CAMINHO_VAZIO"

    @pytest.mark.parametrize("caminho", [123, None, ["app/x.py"], 4.2])
    def test_caminho_de_tipo_errado_falha_sem_excecao(self, workspace, caminho):
        """O contrato promete nunca levantar exceção — nem para tipo errado."""
        result = tool_remover_arquivo(caminho, base_dir=str(workspace))

        assert result["sucesso"] is False
        assert result["codigo"] == "CAMINHO_INVALIDO"
        assert "texto" in result["erro"]

    def test_falha_nunca_devolve_tipo_preenchido(self, workspace):
        """`tipo` é None em toda recusa — inclusive quando o alvo é pasta."""
        pasta = workspace / "app"
        pasta.mkdir()
        (pasta / "main.py").write_text("pass\n", encoding="utf-8")

        recusas = [
            tool_remover_arquivo("app", base_dir=str(workspace)),
            tool_remover_arquivo("nao_existe.py", base_dir=str(workspace)),
            tool_remover_arquivo("../fora.py", base_dir=str(workspace)),
        ]

        assert all(r["sucesso"] is False and r["tipo"] is None for r in recusas)


class TestSeguranca:
    def test_path_traversal_rejeitado_e_alvo_preservado(self, workspace, tmp_path):
        """Critério 3: '..' não escapa do workspace do coder."""
        vitima = tmp_path / "coder" / "tasks.json"
        vitima.write_text("contrato", encoding="utf-8")

        result = tool_remover_arquivo("../tasks.json", base_dir=str(workspace))

        assert result["sucesso"] is False
        assert result["codigo"] == "CAMINHO_INVALIDO"
        assert vitima.exists()

    def test_caminho_absoluto_rejeitado_e_alvo_preservado(self, workspace, tmp_path):
        """Critério 3: caminho absoluto não é aceito quando há base_dir."""
        vitima = tmp_path / "fora.py"
        vitima.write_text("pass\n", encoding="utf-8")

        result = tool_remover_arquivo(str(vitima), base_dir=str(workspace))

        assert result["sucesso"] is False
        assert result["codigo"] == "CAMINHO_INVALIDO"
        assert vitima.exists()

    @pytest.mark.parametrize(
        "protegido", [".git", ".venv", "venv", "node_modules", "__pycache__", ".env"]
    )
    def test_diretorio_protegido_nao_pode_ser_removido(self, workspace, protegido):
        """Critério 4: o próprio diretório sensível é intocável."""
        alvo = workspace / protegido
        alvo.mkdir()

        result = tool_remover_arquivo(protegido, base_dir=str(workspace))

        assert result["sucesso"] is False
        assert result["codigo"] == "DIRETORIO_PROTEGIDO"
        assert alvo.exists()

    def test_arquivo_dentro_de_diretorio_protegido_nao_pode_ser_removido(self, workspace):
        """Critério 4: vale para o conteúdo, não só para a pasta."""
        alvo = workspace / ".git" / "config"
        alvo.parent.mkdir()
        alvo.write_text("[core]\n", encoding="utf-8")

        result = tool_remover_arquivo(".git/config", base_dir=str(workspace))

        assert result["sucesso"] is False
        assert result["codigo"] == "DIRETORIO_PROTEGIDO"
        assert alvo.exists()

    @pytest.mark.parametrize("caminho", [".", "./"])
    def test_raiz_do_workspace_nao_pode_ser_removida(self, workspace, caminho):
        result = tool_remover_arquivo(caminho, base_dir=str(workspace))

        assert result["sucesso"] is False
        assert result["codigo"] == "RAIZ_DO_WORKSPACE"
        assert workspace.exists()

    def test_diretorio_pai_que_e_link_simbolico_nao_escapa(self, workspace, tmp_path):
        """`..` e absoluto são recusados antes — mas um PAI que é link escaparia.

        `unlink()` segue link simbólico de componente intermediário: sem checar o
        pai resolvido, `atalho/importante.py` apagaria fora do workspace.
        """
        externo = tmp_path / "externo"
        externo.mkdir()
        vitima = externo / "importante.py"
        vitima.write_text("dados que não podem sumir\n", encoding="utf-8")
        (workspace / "atalho").symlink_to(externo, target_is_directory=True)

        result = tool_remover_arquivo("atalho/importante.py", base_dir=str(workspace))

        assert result["sucesso"] is False
        assert result["codigo"] == "FORA_DO_WORKSPACE"
        assert vitima.exists(), "o arquivo fora do workspace tem que sobreviver"

    def test_sem_base_dir_tambem_rejeita_absoluto_e_traversal(self, cwd_isolado, tmp_path):
        """Modo legado é destrutivo igual — não pode aceitar caminho de fora."""
        vitima = tmp_path / "fora.py"
        vitima.write_text("pass\n", encoding="utf-8")

        por_absoluto = tool_remover_arquivo(str(vitima))
        por_traversal = tool_remover_arquivo("../fora.py")

        assert por_absoluto["codigo"] == "CAMINHO_INVALIDO"
        assert por_traversal["codigo"] == "CAMINHO_INVALIDO"
        assert vitima.exists()

    def test_link_simbolico_e_removido_sem_tocar_no_alvo(self, workspace, tmp_path):
        """Remover o link não pode remover o que está fora do workspace."""
        alvo_externo = tmp_path / "importante.py"
        alvo_externo.write_text("dados\n", encoding="utf-8")
        link = workspace / "atalho.py"
        link.symlink_to(alvo_externo)

        result = tool_remover_arquivo("atalho.py", base_dir=str(workspace))

        assert result["sucesso"] is True
        assert not link.exists()
        assert alvo_externo.exists(), "o alvo do link permanece intocado"


class TestAuditabilidadeDaTool:
    def test_remocao_bem_sucedida_gera_log(self, workspace, caplog):
        """Critério 6: a remoção deixa rastro do caminho no log da tool."""
        (workspace / "obsoleto.py").write_text("", encoding="utf-8")

        with caplog.at_level("INFO", logger=_LOGGER_DA_TOOL):
            tool_remover_arquivo("obsoleto.py", base_dir=str(workspace))

        assert "obsoleto.py" in caplog.text
        assert "removido" in caplog.text.lower()

    def test_recusa_nao_registra_remocao(self, workspace, caplog):
        with caplog.at_level("INFO", logger=_LOGGER_DA_TOOL):
            tool_remover_arquivo("nao_existe.py", base_dir=str(workspace))

        assert "removido" not in caplog.text.lower()
