"""Testes de regressão para o subsistema de lock de escrita (design_filesystem.py).

Contexto do bug (branch feature/time2-design-fix-lock):
O refactor que introduziu `dirs`/`base_dir` (_resolve_dirs / _resolve_path_arg)
atualizou todas as funções de leitura/escrita, mas NÃO atualizou as três
funções de lock no fim do arquivo — que continuaram chamando
`_resolve_path_arg(filepath)` e `_ensure_dirs()` com as assinaturas antigas.
Resultado: acquire_lock / check_lock / release_lock levantavam
`TypeError: _resolve_path_arg() missing 1 required positional argument: 'dirs'`,
capturado e devolvido como {"status": "error"}.

Como toda escrita (save_artifact/append_artifact/patch_section) exige um lock
ativo, o design_architect nunca conseguia persistir a analise_tecnica_*.md e o
pipeline de design travava (deadlock). Bug secundário: LOCKS_DIR (.locks/) nunca
era criado, então o primeiro os.open(..., O_EXCL) falharia com FileNotFoundError.

Estes testes cobrem:
1. acquire_lock funciona (não levanta TypeError) e cria LOCKS_DIR sob demanda.
2. Um segundo dono é bloqueado; o mesmo dono re-adquire de forma idempotente.
3. check_lock reporta corretamente livre/ocupado.
4. release_lock por não-dono é negado; pelo dono libera e o arquivo volta a ser adquirível.
"""

import pytest

from shared.tools import design_filesystem as df


@pytest.fixture
def isolated_locks(tmp_path, monkeypatch):
    """Isola DESIGN_DIR e LOCKS_DIR em tmp_path.

    LOCKS_DIR é uma constante calculada em import time a partir de DESIGN_DIR;
    monkeypatch em DESIGN_DIR não a atualiza, então patchamos ambas.
    Começa SEM criar .locks/ — parte do contrato é acquire_lock criá-la.
    """
    root = tmp_path / "design"
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    monkeypatch.setattr(df, "DESIGN_DIR", root)
    monkeypatch.setattr(df, "LOCKS_DIR", root / ".locks")
    return root


def test_acquire_lock_nao_levanta_typeerror_e_cria_locks_dir(isolated_locks):
    """Regressão do bug principal: acquire_lock funcionava e criava LOCKS_DIR."""
    assert not (isolated_locks / ".locks").exists()

    result = df.acquire_lock("analise_tecnica_HU-001.md", caller="design_architect")

    assert result["status"] == "ok", result
    assert result["locked"] is True
    assert result["owner"] == "design_architect"
    # Bug secundário: .locks/ precisa ser criado sob demanda.
    assert (isolated_locks / ".locks").is_dir()


def test_acquire_lock_com_alias_de_pasta_resolve_pelo_nome(isolated_locks):
    """O lock é indexado só pelo nome — o alias de pasta é ignorado na resolução.

    Antes do fix, o alias sequer chegava a ser resolvido (TypeError em
    _resolve_path_arg antes de qualquer lógica de lock).
    """
    result = df.acquire_lock("ANALYSIS/analise_tecnica_HU-001.md", caller="design_architect")
    assert result["status"] == "ok", result
    assert result["filepath"] == "analise_tecnica_HU-001.md"

    # Mesmo arquivo, referenciado sem alias, colide com o lock existente.
    other = df.acquire_lock("analise_tecnica_HU-001.md", caller="mermaid_specialist")
    assert other["status"] == "blocked"
    assert other["owner"] == "design_architect"


def test_segundo_dono_e_bloqueado_mesmo_dono_e_idempotente(isolated_locks):
    """Dois especialistas nunca obtêm o mesmo lock; re-aquisição é idempotente."""
    first = df.acquire_lock("relatorio_HU-001.md", caller="markdown_specialist")
    assert first["status"] == "ok"

    blocked = df.acquire_lock("relatorio_HU-001.md", caller="mermaid_specialist")
    assert blocked["status"] == "blocked"
    assert blocked["locked"] is True
    assert blocked["owner"] == "markdown_specialist"

    again = df.acquire_lock("relatorio_HU-001.md", caller="markdown_specialist")
    assert again["status"] == "ok"
    assert again["owner"] == "markdown_specialist"


def test_check_lock_reporta_livre_e_ocupado(isolated_locks):
    """check_lock não levanta TypeError e reflete o estado real do lock."""
    livre = df.check_lock("diagrama_HU-001.mmd", caller="mermaid_specialist")
    assert livre["status"] == "ok"
    assert livre["locked"] is False

    df.acquire_lock("diagrama_HU-001.mmd", caller="mermaid_specialist")

    ocupado = df.check_lock("diagrama_HU-001.mmd", caller="qualquer")
    assert ocupado["status"] == "ok"
    assert ocupado["locked"] is True
    assert ocupado["owner"] == "mermaid_specialist"


def test_release_lock_apenas_dono_libera_e_arquivo_volta_a_ser_adquirivel(isolated_locks):
    """release_lock: negado para não-dono; após liberação, arquivo fica livre."""
    df.acquire_lock("analise_tecnica_HU-002.md", caller="design_architect")

    negado = df.release_lock("analise_tecnica_HU-002.md", caller="intruso")
    assert negado["status"] == "blocked"
    assert negado["released"] is False
    assert negado["owner"] == "design_architect"

    liberado = df.release_lock("analise_tecnica_HU-002.md", caller="design_architect")
    assert liberado["status"] == "ok"
    assert liberado["released"] is True

    # Livre novamente → outro especialista consegue adquirir.
    reacquired = df.acquire_lock("analise_tecnica_HU-002.md", caller="mermaid_specialist")
    assert reacquired["status"] == "ok"
    assert reacquired["owner"] == "mermaid_specialist"


def test_ciclo_completo_desbloqueia_escrita(isolated_locks):
    """Ponta-a-ponta do fix: com lock adquirido, save_artifact deixa de ser bloqueado.

    Reproduz o caminho que estava travado: sem um lock ativo, save_artifact
    retorna 'blocked'; com o lock do próprio caller, a escrita é permitida.
    """
    fname = "analise_tecnica_HU-001_HU-002.md"

    sem_lock = df.save_artifact(fname, "# Análise\n", caller="design_architect")
    assert sem_lock["status"] == "blocked"

    acquired = df.acquire_lock(fname, caller="design_architect")
    assert acquired["status"] == "ok"

    escrito = df.save_artifact(fname, "# Análise\n", caller="design_architect")
    assert escrito["status"] == "ok", escrito
    assert (isolated_locks / "analysis" / fname).is_file()
