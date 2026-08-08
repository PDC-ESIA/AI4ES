"""I/O do subagente receive_requirements: paths de workspace, slugs e persistência de arquivos/doubt artifacts."""

import base64
import re
from datetime import datetime, timezone
from pathlib import Path

from shared.workspace import get_agent_workspace, get_workspace_root

_SOURCE_SUFFIXES = {".py", ".java", ".js", ".ts", ".c", ".cpp"}

_PYTEST_IMPORT_BOOTSTRAP = '''"""Bootstrap de imports gerado automaticamente pelo QA."""

import sys
from pathlib import Path


_SUITE_DIR = Path(__file__).resolve().parent
for _IMPORT_DIR in (_SUITE_DIR / "src", _SUITE_DIR):
    _IMPORT_PATH = str(_IMPORT_DIR)
    if _IMPORT_DIR.is_dir():
        while _IMPORT_PATH in sys.path:
            sys.path.remove(_IMPORT_PATH)
        sys.path.insert(0, _IMPORT_PATH)
'''


def _tests_dir() -> Path:
    """workspace_output/tests/inputs/ resolvido em runtime.

    Centraliza o destino dos arquivos pytest gerados pelo subagente.
    Resolvido em runtime para respeitar WORKSPACE_OUTPUT_DIR env var.
    """
    return get_agent_workspace("receive_requirements")


def _doubt_dir() -> Path:
    """Sibling 'doubt_artifacts' dentro do diretório de testes."""
    return _tests_dir() / "doubt_artifacts"


async def _gerar_doubt_artifact(id_artefato: str, motivo: str) -> str:
    """Gera arquivo de doubt artifact para artefato bloqueado.

    Args:
        id_artefato: Identificador do artefato.
        motivo: Motivo do bloqueio.

    Returns:
        str: Caminho do arquivo gerado.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    _doubt_dir().mkdir(parents=True, exist_ok=True)

    nome = f"Doubt_Artifact_{id_artefato}_{timestamp}.md"
    caminho = _doubt_dir() / nome

    conteudo = f"""# Doubt Artifact — QA Agent

**ID do Artefato:** {id_artefato}
**Data/Hora:** {timestamp}
**Agente:** qa_agent
**Status:** BLOQUEADO — aguardando intervenção humana

---

## Descrição do Bloqueio

{motivo}

## O que é necessário para continuar

[ Preencher após intervenção ]

## Resolução

- **Resolvido por:** [ Preencher ]
- **Data:** [ Preencher ]
- **Ação tomada:** [ Preencher ]
"""
    caminho.write_text(conteudo, encoding="utf-8")
    return str(caminho)


def _slugify(texto: str) -> str:
    """Normaliza texto para uso em nomes de arquivo.

    Args:
        texto: Texto a normalizar.

    Returns:
        str: Slug seguro para nomes de arquivo.
    """
    base = (texto or "artefato").strip().lower()
    base = re.sub(r"[^a-z0-9]+", "_", base)
    base = base.strip("_")
    return base or "artefato"


def _safe_filename(nome: str) -> str:
    """Sanitiza nome de arquivo removendo caracteres especiais.

    Args:
        nome: Nome original do arquivo.

    Returns:
        str: Nome seguro para filesystem.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", (nome or "arquivo.txt").strip())
    cleaned = cleaned.lstrip(".")
    return cleaned or "arquivo.txt"


def _descobrir_fontes_persistidos() -> list[Path]:
    """Descobre fontes no output do Coder sem depender do estado de outro agente.

    O workspace é reinicializado pelo Orchestrator a cada solicitação, portanto
    qualquer arquivo encontrado em ``coder/src`` pertence à execução atual.
    A leitura é feita exclusivamente pelo QA e não exige que Coding publique um
    manifesto ou altere seu contrato.
    """
    coder_root = get_agent_workspace("cr_coder").resolve()
    if not coder_root.exists():
        return []

    sources = []
    for path in sorted(coder_root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in _SOURCE_SUFFIXES:
            continue
        relative_parts = {part.casefold() for part in path.relative_to(coder_root).parts}
        if "__pycache__" in relative_parts or "tests" in relative_parts:
            continue
        if path.name == "conftest.py" or path.name.startswith("test_"):
            continue
        sources.append(path.resolve())
    return sources


def _salvar_bootstrap_pytest(destino: Path) -> Path:
    """Torna imports dos fontes materializados reproduzíveis fora do runner.

    Quando o Coder entrega ``src/init.py`` ou omite o marcador do pacote, cria
    um ``src/__init__.py`` somente na cópia de testes. Isso evita que
    ``import src`` resolva para o pacote interno do próprio ADK, sem modificar
    nenhum arquivo de produção.
    """
    tests_root = get_agent_workspace("receive_requirements").resolve()
    destino = destino.resolve()
    if not destino.is_relative_to(tests_root):
        raise ValueError("A suíte deve permanecer dentro de tests/inputs.")

    source_dir = destino / "src"
    if source_dir.is_dir() and any(source_dir.glob("*.py")):
        package_marker = source_dir / "__init__.py"
        if not package_marker.exists():
            package_marker.write_text(
                '"""Marcador de pacote criado no workspace de teste pelo QA."""\n',
                encoding="utf-8",
            )

    caminho = destino / "conftest.py"
    caminho.write_text(_PYTEST_IMPORT_BOOTSTRAP, encoding="utf-8")
    return caminho


def _salvar_arquivos_apoio(artefato: dict, destino: Path) -> list[Path]:
    """Salva arquivos de apoio preservando a topologia dos fontes do Coder.

    Args:
        artefato: Dicionário contendo lista de arquivos_apoio.
        destino: Path do diretório onde arquivos serão salvos.

    Returns:
        list[Path]: Lista de paths dos arquivos salvos.
    """
    arquivos = artefato.get("arquivos_apoio", [])
    if not isinstance(arquivos, list):
        arquivos = []

    # O manifesto de Coding é opcional. O QA complementa qualquer lista
    # recebida com os fontes realmente persistidos pelo Coder, sem exigir
    # mudanças nos agentes de Requirements, Design ou Coding.
    workspace_root = get_workspace_root().resolve()
    provided_paths = {
        item.get("path")
        for item in arquivos
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    arquivos = list(arquivos)
    for source in _descobrir_fontes_persistidos():
        relative_path = source.relative_to(workspace_root).as_posix()
        if relative_path not in provided_paths:
            arquivos.append({"path": relative_path})
            provided_paths.add(relative_path)

    salvos: list[Path] = []
    destino = destino.resolve()
    coder_root = get_agent_workspace("cr_coder").resolve()
    for item in arquivos:
        if not isinstance(item, dict):
            continue

        source_path = item.get("path")
        source: Path | None = None
        if isinstance(source_path, str) and source_path.strip():
            workspace_root = get_workspace_root().resolve()
            candidate = Path(source_path).expanduser()
            if not candidate.is_absolute():
                candidate = workspace_root / candidate
            candidate = candidate.resolve()
            if candidate.is_file() and candidate.is_relative_to(workspace_root):
                source = candidate

        nome = _safe_filename(
            item.get("nome")
            or item.get("filename")
            or (source.name if source else "arquivo.txt")
        )
        conteudo_texto = item.get("conteudo")
        conteudo_b64 = item.get("conteudo_base64")

        # Manter ``src/checkout.py`` como ``<artefato>/src/checkout.py`` é
        # essencial para imports de pacote (``from src.checkout import ...``).
        # O nome sugerido pelo LLM pode conter barras e ser sanitizado para
        # ``src_checkout.py``; para fontes persistidos, o path real do Coder é
        # a fonte canônica da topologia.
        if source is not None and source.is_relative_to(coder_root):
            caminho = destino / source.relative_to(coder_root)
        else:
            caminho = destino / nome
        caminho = caminho.resolve()
        if not caminho.is_relative_to(destino):
            continue
        caminho.parent.mkdir(parents=True, exist_ok=True)

        if source is not None:
            caminho.write_bytes(source.read_bytes())
            salvos.append(caminho)
            continue

        if isinstance(conteudo_texto, str):
            caminho.write_text(conteudo_texto, encoding="utf-8")
            salvos.append(caminho)
            continue

        if isinstance(conteudo_b64, str):
            try:
                bruto = base64.b64decode(conteudo_b64)
            except Exception:
                continue
            caminho.write_bytes(bruto)
            salvos.append(caminho)

    return salvos
