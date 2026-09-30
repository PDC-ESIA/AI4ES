"""Testes da impressão digital do workspace (issue #394).

Esta medida sustenta um dos gatilhos de travamento do loop `coder ↔ executor`:
"o coder devolveu o turno sem alterar nada". Os dois modos de erro são
assimétricos e ambos custam caro:

- hash MUDAR sem o conteúdo mudar → a estagnação nunca é detectada e o loop
  queima iterações reproduzindo a mesma falha;
- hash NÃO mudar quando algo mudou → o loop pode ser cortado no meio de um
  avanço real.

Por isso os testes aqui insistem em invariância (mesmo conteúdo, contextos
diferentes) e em sensibilidade (qualquer alteração real muda o hash).
"""

import os

import pytest

from shared.execution.workspace_fingerprint import fingerprint_workspace


def _workspace(raiz, arquivos: dict[str, str]):
    raiz.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in arquivos.items():
        destino = raiz / nome
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
    return raiz


_ARTEFATO = {
    "run.json": '{"surface": "none", "test": ["pytest"]}',
    "app/main.py": "print('oi')\n",
    "app/util.py": "def f():\n    return 1\n",
}


# ---------------------------------------------------------------------------
# Invariância — mesmo conteúdo, mesma impressão digital
# ---------------------------------------------------------------------------


def test_mesmo_conteudo_produz_mesmo_hash(tmp_path):
    a = _workspace(tmp_path / "a", _ARTEFATO)
    b = _workspace(tmp_path / "b", _ARTEFATO)

    assert fingerprint_workspace(a) == fingerprint_workspace(b)


def test_hash_nao_muda_quando_so_o_mtime_muda(tmp_path):
    """O artefato é copiado a cada rodada; `mtime` mudaria sem o código mudar.

    Se o hash seguisse `mtime`, toda rodada pareceria ter alteração e a
    estagnação nunca seria detectada — justamente o que este sinal existe para
    pegar.
    """
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)
    antes = fingerprint_workspace(raiz)

    os.utime(raiz / "app/main.py", (0, 0))

    assert fingerprint_workspace(raiz) == antes


def test_hash_independe_da_ordem_de_criacao(tmp_path):
    """A ordem de iteração do filesystem não é garantida; o hash não pode depender dela."""
    a = _workspace(tmp_path / "a", {"z.py": "1", "m.py": "2", "a.py": "3"})
    b = _workspace(tmp_path / "b", {"a.py": "3", "z.py": "1", "m.py": "2"})

    assert fingerprint_workspace(a) == fingerprint_workspace(b)


def test_chamadas_repetidas_sao_estaveis(tmp_path):
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)

    assert fingerprint_workspace(raiz) == fingerprint_workspace(raiz)


# ---------------------------------------------------------------------------
# Sensibilidade — qualquer alteração real muda a impressão digital
# ---------------------------------------------------------------------------


def test_editar_conteudo_muda_o_hash(tmp_path):
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)
    antes = fingerprint_workspace(raiz)

    (raiz / "app/main.py").write_text("print('outro')\n", encoding="utf-8")

    assert fingerprint_workspace(raiz) != antes


def test_acrescentar_arquivo_muda_o_hash(tmp_path):
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)
    antes = fingerprint_workspace(raiz)

    (raiz / "app/novo.py").write_text("x = 1\n", encoding="utf-8")

    assert fingerprint_workspace(raiz) != antes


def test_remover_arquivo_muda_o_hash(tmp_path):
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)
    antes = fingerprint_workspace(raiz)

    (raiz / "app/util.py").unlink()

    assert fingerprint_workspace(raiz) != antes


def test_renomear_sem_alterar_conteudo_muda_o_hash(tmp_path):
    """Renomear é alteração real: o caminho entra no hash junto com o conteúdo."""
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)
    antes = fingerprint_workspace(raiz)

    (raiz / "app/util.py").rename(raiz / "app/helpers.py")

    assert fingerprint_workspace(raiz) != antes


def test_mover_conteudo_entre_arquivos_muda_o_hash(tmp_path):
    """Guarda contra hash sem separador: 'ab'+'c' não pode colidir com 'a'+'bc'."""
    a = _workspace(tmp_path / "a", {"ab": "c"})
    b = _workspace(tmp_path / "b", {"a": "bc"})

    assert fingerprint_workspace(a) != fingerprint_workspace(b)


def test_manifesto_e_dependencias_contam_como_alteracao(tmp_path):
    """Não-código também é artefato: o gate de executabilidade já trata assim."""
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)
    antes = fingerprint_workspace(raiz)

    (raiz / "run.json").write_text('{"surface": "command"}', encoding="utf-8")

    assert fingerprint_workspace(raiz) != antes


def test_arquivo_sem_extensao_conta(tmp_path):
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)
    antes = fingerprint_workspace(raiz)

    (raiz / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")

    assert fingerprint_workspace(raiz) != antes


# ---------------------------------------------------------------------------
# Ruído gerado não pode contar como progresso
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "gerado",
    ["__pycache__/main.cpython-312.pyc", "node_modules/x/index.js", ".venv/pyvenv.cfg"],
)
def test_diretorio_gerado_nao_afeta_o_hash(tmp_path, gerado):
    """Build/caches mudam sozinhos; contá-los mascararia a estagnação."""
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)
    antes = fingerprint_workspace(raiz)

    destino = raiz / gerado
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("gerado", encoding="utf-8")

    assert fingerprint_workspace(raiz) == antes


# ---------------------------------------------------------------------------
# Bordas
# ---------------------------------------------------------------------------


def test_workspace_vazio_e_inexistente_coincidem(tmp_path):
    """Sem artefato nenhum é a mesma situação nos dois casos."""
    vazio = tmp_path / "vazio"
    vazio.mkdir()

    assert fingerprint_workspace(vazio) == fingerprint_workspace(
        tmp_path / "nao_existe"
    )


def test_workspace_com_arquivo_nao_coincide_com_vazio(tmp_path):
    vazio = tmp_path / "vazio"
    vazio.mkdir()
    com_arquivo = _workspace(tmp_path / "ws", {"a.py": ""})

    assert fingerprint_workspace(com_arquivo) != fingerprint_workspace(vazio)


def test_symlink_e_ignorado(tmp_path):
    """Seguir link levaria para fora do workspace; o alvo não é obra do coder."""
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)
    antes = fingerprint_workspace(raiz)

    externo = tmp_path / "externo.py"
    externo.write_text("segredo\n", encoding="utf-8")
    try:
        (raiz / "link.py").symlink_to(externo)
    except (OSError, NotImplementedError):
        pytest.skip("filesystem sem suporte a symlink")

    assert fingerprint_workspace(raiz) == antes


def test_arquivo_ilegivel_nao_estoura(tmp_path):
    """Derrubar o callback por um arquivo ilegível custaria a rodada inteira."""
    raiz = _workspace(tmp_path / "ws", _ARTEFATO)
    alvo = raiz / "app/main.py"
    alvo.chmod(0o000)

    try:
        if os.access(alvo, os.R_OK):  # root ignora permissão de arquivo
            pytest.skip("processo consegue ler arquivo sem permissão (root)")
        assert isinstance(fingerprint_workspace(raiz), str)
    finally:
        alvo.chmod(0o644)
