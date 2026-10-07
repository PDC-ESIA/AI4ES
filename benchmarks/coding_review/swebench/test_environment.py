"""Testes da preparação do workspace e da guarda do ambiente (Docker falso)."""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest
from docker.errors import ImageNotFound

from benchmarks.coding_review.swebench import environment
from benchmarks.coding_review.swebench._testutils import (
    ADK_DIR,
    load_isolated_module,
    module_constant,
)

IMAGEM = "swebench/sweb.eval.x86_64.django_1776_django-11099:latest"


# ---------------------------------------------------------------------------
# Docker falso: só o que `extract_testbed` usa
# ---------------------------------------------------------------------------


class _Container:
    def __init__(self, tar_bytes: bytes):
        self._tar = tar_bytes
        self.removido = False

    def get_archive(self, caminho: str):
        assert caminho == environment.TESTBED_DIR
        return iter([self._tar[:100], self._tar[100:]]), {}

    def remove(self, force: bool = False):
        self.removido = True


class _Images:
    def __init__(self, presente: bool):
        self.presente = presente
        self.pulls: list[tuple[str, str]] = []

    def get(self, imagem: str):
        if not self.presente:
            raise ImageNotFound("ausente")
        return object()

    def pull(self, repositorio: str, tag: str | None = None):
        self.pulls.append((repositorio, tag))


class _Containers:
    def __init__(self, tar_bytes: bytes):
        self._tar = tar_bytes
        self.criados: list[_Container] = []

    def create(self, imagem: str, command=None):
        container = _Container(self._tar)
        self.criados.append(container)
        return container


class _Client:
    def __init__(self, tar_bytes: bytes, *, imagem_presente: bool = True):
        self.images = _Images(imagem_presente)
        self.containers = _Containers(tar_bytes)


def _tar_de_diretorio(origem: Path, *, extras: list[tarfile.TarInfo] = ()) -> bytes:
    """Empacota `origem` como `testbed/` (igual ao `get_archive('/testbed')`)."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        tar.add(origem, arcname="testbed")
        for info in extras:
            tar.addfile(info)
    return buffer.getvalue()


def _repo_git(raiz: Path, *, com_dockerfile: bool = False) -> Path:
    (raiz / "pkg").mkdir(parents=True)
    (raiz / "pkg" / "mod.py").write_text("X = 1\n")
    if com_dockerfile:
        (raiz / "Dockerfile").write_text("FROM python:3\n")
    ident = ["-c", "user.name=b", "-c", "user.email=b@example.com"]
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "base"]):
        subprocess.run(["git", *ident, "-C", str(raiz), *args], check=True)
    return raiz


# ---------------------------------------------------------------------------
# Arquivos do benchmark
# ---------------------------------------------------------------------------


def test_dockerfile_usa_a_imagem_oficial_e_o_env_testbed():
    texto = environment.render_dockerfile(IMAGEM)
    assert f"FROM {IMAGEM}" in texto
    assert "ENV PATH=/opt/miniconda3/envs/testbed/bin:$PATH" in texto
    # Código no caminho da avaliação oficial; /app (workdir do sandbox) é o link.
    assert "COPY . /testbed" in texto
    assert "ln -s /testbed /app" in texto
    assert texto.index("rm -rf /testbed") < texto.index("COPY . /testbed")
    assert texto.rstrip().endswith("WORKDIR /testbed")


def test_workdir_do_container_bate_com_o_sandbox_da_producao():
    sandbox = ADK_DIR / "shared" / "execution" / "sandbox.py"
    assert module_constant(sandbox, "_DOCKER_WORKDIR") == environment.CONTAINER_WORKDIR


def test_manifesto_semeado_e_aceito_pelo_harness(tmp_path: Path):
    manifest_mod = load_isolated_module(
        ADK_DIR / "shared" / "execution" / "manifest.py", "_swebench_manifest"
    )
    environment.write_benchmark_files(tmp_path, IMAGEM)
    manifesto = manifest_mod.load_manifest(tmp_path / "run.json")
    assert manifesto.sandbox == "docker"
    assert manifesto.surface == "none"
    assert manifesto.test == []


def test_ambiente_intacto_nao_gera_ocorrencia(tmp_path: Path):
    environment.write_benchmark_files(tmp_path, IMAGEM)
    assert environment.ensure_benchmark_files(tmp_path, IMAGEM) == []


def test_restaura_dockerfile_e_dockerignore(tmp_path: Path):
    environment.write_benchmark_files(tmp_path, IMAGEM)
    (tmp_path / "Dockerfile").unlink()
    (tmp_path / ".dockerignore").write_text("")

    ocorrencias = environment.ensure_benchmark_files(tmp_path, IMAGEM)

    assert ocorrencias == [
        environment.VIOLACAO_DOCKERFILE,
        environment.VIOLACAO_DOCKERIGNORE,
    ]
    assert (tmp_path / "Dockerfile").read_text() == environment.render_dockerfile(IMAGEM)
    assert (tmp_path / ".dockerignore").read_text() == ".git\n"


def test_forca_sandbox_docker_preservando_o_resto(tmp_path: Path):
    environment.write_benchmark_files(tmp_path, IMAGEM)
    manifesto = {"surface": "none", "sandbox": "direct", "test": ["python -m pytest t.py"]}
    (tmp_path / "run.json").write_text(json.dumps(manifesto))

    ocorrencias = environment.ensure_benchmark_files(tmp_path, IMAGEM)

    assert ocorrencias == [environment.VIOLACAO_SANDBOX]
    salvo = json.loads((tmp_path / "run.json").read_text())
    assert salvo["sandbox"] == "docker"
    assert salvo["test"] == ["python -m pytest t.py"]


@pytest.mark.parametrize(
    "conteudo, esperado",
    [
        (None, environment.OBSERVACAO_RUN_JSON_AUSENTE),
        ("{não é json", environment.OBSERVACAO_RUN_JSON_INVALIDO),
        ("[1, 2]", environment.OBSERVACAO_RUN_JSON_INVALIDO),
    ],
)
def test_run_json_ausente_ou_invalido_so_e_registrado(tmp_path: Path, conteudo, esperado):
    environment.write_benchmark_files(tmp_path, IMAGEM)
    if conteudo is None:
        (tmp_path / "run.json").unlink()
    else:
        (tmp_path / "run.json").write_text(conteudo)
    assert environment.ensure_benchmark_files(tmp_path, IMAGEM) == [esperado]


def test_detecta_virtualenv_no_manifesto(tmp_path: Path):
    environment.write_benchmark_files(tmp_path, IMAGEM)
    manifesto = {
        "surface": "none",
        "sandbox": "docker",
        "build": ["python -m venv venv", "venv/bin/pip install -e ."],
    }
    (tmp_path / "run.json").write_text(json.dumps(manifesto))
    assert environment.ensure_benchmark_files(tmp_path, IMAGEM) == [
        environment.OBSERVACAO_VENV
    ]


# ---------------------------------------------------------------------------
# Extração do /testbed e preparação do workspace
# ---------------------------------------------------------------------------


def test_extrai_testbed_e_pula_link_inseguro(tmp_path: Path):
    origem = tmp_path / "origem"
    (origem / "pkg").mkdir(parents=True)
    (origem / "pkg" / "mod.py").write_text("X = 1\n")
    link_inseguro = tarfile.TarInfo("testbed/link_absoluto")
    link_inseguro.type = tarfile.SYMTYPE
    link_inseguro.linkname = "/etc/passwd"
    cliente = _Client(_tar_de_diretorio(origem, extras=[link_inseguro]))

    destino = tmp_path / "coder" / "src"
    pulados = environment.extract_testbed(IMAGEM, destino, client=cliente)

    assert (destino / "pkg" / "mod.py").read_text() == "X = 1\n"
    assert not (destino / "link_absoluto").exists()
    assert pulados == ["testbed/link_absoluto"]
    assert cliente.containers.criados[0].removido
    assert cliente.images.pulls == []


def test_baixa_a_imagem_quando_ausente(tmp_path: Path):
    origem = tmp_path / "origem"
    origem.mkdir()
    (origem / "a.py").write_text("")
    cliente = _Client(_tar_de_diretorio(origem), imagem_presente=False)
    environment.extract_testbed(IMAGEM, tmp_path / "dest", client=cliente)
    assert cliente.images.pulls == [
        ("swebench/sweb.eval.x86_64.django_1776_django-11099", "latest")
    ]


def test_extracao_exige_destino_vazio(tmp_path: Path):
    destino = tmp_path / "dest"
    destino.mkdir()
    (destino / "sobra.txt").write_text("x")
    cliente = _Client(_tar_de_diretorio(destino))
    with pytest.raises(environment.EnvironmentPreparationError, match="não está vazio"):
        environment.extract_testbed(IMAGEM, destino, client=cliente)


def test_seed_workspace_fotografa_antes_dos_arquivos_do_benchmark(tmp_path: Path):
    repo = _repo_git(tmp_path / "origem")
    cliente = _Client(_tar_de_diretorio(repo))
    workspace = tmp_path / "coder" / "src"

    resultado = environment.seed_workspace(workspace, IMAGEM, client=cliente)

    assert len(resultado.baseline_tree) == 40
    assert resultado.conflicts == []
    for nome in environment.BENCHMARK_FILES:
        assert (workspace / nome).is_file()
    assert (workspace / "pkg" / "mod.py").is_file()


def test_seed_workspace_registra_conflito_com_arquivo_do_repo(tmp_path: Path):
    repo = _repo_git(tmp_path / "origem", com_dockerfile=True)
    cliente = _Client(_tar_de_diretorio(repo))
    resultado = environment.seed_workspace(tmp_path / "coder" / "src", IMAGEM, client=cliente)
    assert resultado.conflicts == ["Dockerfile"]


def test_seed_workspace_registra_ignorados_ja_existentes(tmp_path: Path):
    repo = _repo_git(tmp_path / "origem")
    (repo / ".gitignore").write_text("*.so\n")
    (repo / "pkg" / "_ext.so").write_bytes(b"\x7fELF")
    cliente = _Client(_tar_de_diretorio(repo))
    resultado = environment.seed_workspace(tmp_path / "coder" / "src", IMAGEM, client=cliente)
    assert resultado.baseline_ignored == frozenset({"pkg/_ext.so"})
