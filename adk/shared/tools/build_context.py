"""Reúne o contexto de build de um workspace num texto único (determinístico).

Alimenta o `dockerfile_resolver`: em vez de dar ao agente uma tool de filesystem
(capacidade de vasculhar por conta própria), o `ExecutorOrchestrator` chama esta
função ANTES de invocar o agente e injeta o texto na conversa — mesmo truque do
`REPORT_PATH:` que já entrega dado ao validador sem tool. Não decide nada: só
coleta e formata (estrutura + manifestos + README + configs de CI).
"""

from __future__ import annotations

from pathlib import Path

# Diretórios de dependências/build/VCS — ruído, nunca entram na listagem.
_EXCLUIR_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"}

# Manifestos conhecidos (checagem de presença — sem adivinhar quais existem).
_MANIFESTOS = (
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "pom.xml",
    "go.mod",
    "Cargo.toml",
    "build.gradle",
    "Gemfile",
    "composer.json",
)
_MANIFESTO_GLOBS = ("*.csproj",)

_CI_GLOBS = (".github/workflows/*.yml", ".github/workflows/*.yaml")
_CI_FIXOS = (".gitlab-ci.yml", ".circleci/config.yml", ".travis.yml")

_MAX_PROFUNDIDADE = 3
_MAX_BYTES_ARQUIVO = 8000  # teto por manifesto/README/CI lido


def _listar_arvore(raiz: Path) -> list[str]:
    """Caminhos relativos (arquivos e dirs) até `_MAX_PROFUNDIDADE`, sem dirs de deps/VCS."""
    itens: list[str] = []

    def _rec(dir_atual: Path, prof: int) -> None:
        try:
            entradas = sorted(dir_atual.iterdir(), key=lambda p: p.name)
        except OSError:
            return
        for p in entradas:
            if p.is_dir() and p.name in _EXCLUIR_DIRS:
                continue
            rel = p.relative_to(raiz).as_posix()
            itens.append(rel + ("/" if p.is_dir() else ""))
            if p.is_dir() and prof < _MAX_PROFUNDIDADE:
                _rec(p, prof + 1)

    _rec(raiz, 1)
    return itens


def _ler_truncado(caminho: Path) -> str:
    try:
        txt = caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(txt) > _MAX_BYTES_ARQUIVO:
        txt = txt[:_MAX_BYTES_ARQUIVO] + "\n... [truncado] ..."
    return txt


def _secao(titulo: str, corpo: str) -> str:
    return f"===== {titulo} =====\n{corpo.rstrip()}\n"


def reunir_contexto_build(coder_dir: Path, tech_stack: list[str] | None = None) -> str:
    """Reúne o contexto de build do `coder_dir` num texto pronto para a conversa.

    Determinístico e sem LLM/tool: apenas coleta e formata o que existe. Sempre
    devolve texto (nunca levanta) — workspace inexistente vira uma seção honesta.

    `tech_stack` (quando não-vazio) entra como uma DICA no topo — não é
    autoritativa (mesma lógica de `contract.interfaces` para o validador). Com o
    default `None`, a saída é idêntica à de antes (F1 não passa o parâmetro).
    """
    coder_dir = Path(coder_dir)

    partes: list[str] = []
    if tech_stack:
        partes.append(_secao(
            "TECH STACK DECLARADA (dica, não autoritativa)",
            "\n".join(str(t) for t in tech_stack),
        ))

    if not coder_dir.is_dir():
        partes.append(_secao("ESTRUTURA DO WORKSPACE", "(workspace inexistente)"))
        return "\n".join(partes)

    arvore = _listar_arvore(coder_dir)
    partes.append(_secao("ESTRUTURA DO WORKSPACE", "\n".join(arvore) if arvore else "(vazio)"))

    # Manifestos (presença pura + globs)
    for nome in _MANIFESTOS:
        p = coder_dir / nome
        if p.is_file():
            partes.append(_secao(f"MANIFESTO: {nome}", _ler_truncado(p)))
    for glob in _MANIFESTO_GLOBS:
        for p in sorted(coder_dir.glob(glob)):
            if p.is_file():
                partes.append(_secao(f"MANIFESTO: {p.name}", _ler_truncado(p)))

    # README (o primeiro basta)
    for p in sorted(coder_dir.glob("README*")):
        if p.is_file():
            partes.append(_secao(f"README: {p.name}", _ler_truncado(p)))
            break

    # Configs de CI
    ci_files: list[Path] = []
    for glob in _CI_GLOBS:
        ci_files += sorted(coder_dir.glob(glob))
    for rel in _CI_FIXOS:
        p = coder_dir / rel
        if p.is_file():
            ci_files.append(p)
    for p in ci_files:
        if p.is_file():
            partes.append(_secao(f"CI: {p.relative_to(coder_dir).as_posix()}", _ler_truncado(p)))

    return "\n".join(partes)
