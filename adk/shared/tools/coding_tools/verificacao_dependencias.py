"""Verificação estática de dependências: imports de terceiros × requirements.txt.

Confronta o que o código efetivamente importa com o que está declarado no
`requirements.txt`, apontando divergências ANTES de pagar o custo do build da
imagem Docker. É a classe de falha nº 1 do agente de codificação: dependência
importada mas não declarada só aparece hoje como falha de build, no estágio 2 do
harness.

Este módulo é deliberadamente **puro**: só stdlib, sem Docker, sem Pydantic, sem
importar o harness. Recebe um diretório, devolve uma lista de dicionários. Quem
transforma achado em `StageResult` — e quem decide se reprova — é o harness
(`harness_execucao.py::_estagio_verificacao_estatica`).

Política de severidade (decisão D9 do plano de Feedforward)
-----------------------------------------------------------
Só existe **um** caso inequívoco, e é o único marcado como ``critical``:
não existe `requirements.txt` e há imports de terceiros. Todo o resto —
divergência de nome, alias desconhecido — sai como ``info``.

O motivo é assimetria de custo: o pior caso de deixar passar é o comportamento
de hoje (o erro aparece no build); o pior caso de bloquear indevidamente é
**pior** que hoje — aborta o run, devolve ao coder um erro que não existe e pode
induzi-lo a declarar um pacote inexistente, virando falha real. Nome de import
raramente é igual ao nome do pacote (`PIL` → `Pillow`), e a tabela de alias
nunca fica completa.

Import transitivo: a terceira categoria
---------------------------------------
Entre "declarado" e "faltando" existe um caso intermediário: o módulo não está
no `requirements.txt`, mas vem instalado junto com um pacote que está — o coder
importa `Jinja2Templates` de `starlette.templating` e declara só `fastapi`, que
traz o Starlette. O achado é verdadeiro (não está declarado) e **não é
acionável**: declarar uma transitiva duplica o pin e pode conflitar com a faixa
de versão que o pacote provedor exige.

Ele sai como `import_transitivo`, `info` — registrado, nunca suprimido: este
módulo descreve, não julga. Quem agrega é que separa ruído de sinal, e o harness
já entrega a contagem pronta em `evidence["acionaveis"]`.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

__all__ = [
    "verificar_dependencias",
    "ALIAS_IMPORT_PARA_PACOTE",
    "TRANSITIVOS_CONHECIDOS",
]


# ---------------------------------------------------------------------------
# Nome de import ≠ nome de pacote PyPI
# ---------------------------------------------------------------------------
# Sem esta tabela, todo import da esquerda vira falso positivo. Ela nunca fica
# completa — é exatamente por isso que a divergência de nome NÃO reprova (D9).
ALIAS_IMPORT_PARA_PACOTE: dict[str, str] = {
    "jose": "python-jose",
    "dotenv": "python-dotenv",
    "jwt": "PyJWT",
    "multipart": "python-multipart",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
}

# ---------------------------------------------------------------------------
# Pacote declarado → módulos que ele já traz instalados
# ---------------------------------------------------------------------------
# Chave: nome da distribuição PyPI como aparece no requirements (normalizada na
# consulta). Valor: nomes de IMPORT que ela disponibiliza por tabela.
#
# Não precisa ser completa — cobre o que apareceria de forma recorrente. O caso
# que a motiva é o `starlette` sob `fastapi`: basta uma rota renderizar template
# para o achado aparecer, e ele sozinho satura a evidência de um projeto inteiro.
#
# Resolver isso de verdade (lendo os metadados dos pacotes) é impossível neste
# estágio: ele roda ANTES do build, então as dependências do app gerado não estão
# instaladas em lugar nenhum — nem no venv do ADK, nem na imagem.
TRANSITIVOS_CONHECIDOS: dict[str, tuple[str, ...]] = {
    "fastapi": ("starlette", "pydantic"),
    "uvicorn": ("click", "h11"),
}

# Ordem de busca idêntica à do `harness_docker._detect_requirements`. Reimplementado
# aqui de propósito: importar de lá acoplaria este módulo puro ao módulo de Docker.
_NOMES_REQUIREMENTS = (
    "requirements.txt",
    "requirements/base.txt",
    "requirements/prod.txt",
)

_DIRS_IGNORADOS = {
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".git",
    ".mypy_cache",
}

# Separa o nome do pacote dos specifiers: `uvicorn[standard]>=0.30 ; python_version<"4"`
_SEPARADORES_REQUISITO = re.compile(r"[\[\]<>=!~;,\s@]")


def _normalizar(nome: str) -> str:
    """Normaliza nome de distribuição conforme PEP 503 (lowercase, `-_.` → `-`)."""
    return re.sub(r"[-_.]+", "-", nome).lower()


def _ler_requirements(coder_dir: Path) -> tuple[Path | None, set[str]]:
    """Localiza o requirements e devolve (caminho, nomes normalizados declarados)."""
    for nome in _NOMES_REQUIREMENTS:
        candidato = coder_dir / nome
        if candidato.is_file():
            break
    else:
        return None, set()

    declarados: set[str] = set()
    try:
        linhas = candidato.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return candidato, declarados

    for linha in linhas:
        linha = linha.split("#", 1)[0].strip()
        if not linha or linha.startswith("-"):
            continue  # opções (-r, -e, --index-url) não declaram pacote
        pacote = _SEPARADORES_REQUISITO.split(linha, maxsplit=1)[0].strip()
        if pacote:
            declarados.add(_normalizar(pacote))

    return candidato, declarados


def _transitivos_disponiveis(declarados: set[str]) -> dict[str, str]:
    """Módulo importável por tabela → pacote declarado que o traz.

    Só considera provedores efetivamente presentes no requirements: sem
    `fastapi` declarado, `starlette` volta a ser um achado legítimo. Em caso de
    dois provedores para o mesmo módulo, vence o primeiro da tabela — a ordem do
    literal é estável, então a saída continua determinística.
    """
    providos: dict[str, str] = {}
    for pacote, modulos in TRANSITIVOS_CONHECIDOS.items():
        if _normalizar(pacote) not in declarados:
            continue
        for modulo in modulos:
            providos.setdefault(modulo, pacote)
    return providos


def _nomes_locais(coder_dir: Path) -> set[str]:
    """Módulos/pacotes do próprio projeto — nunca são dependência externa.

    Deliberadamente generoso (varre em profundidade): errar para o lado de
    considerar local reduz falso positivo, que é o modo de falha caro aqui.
    """
    locais: set[str] = set()
    for caminho in coder_dir.rglob("*"):
        if any(parte in _DIRS_IGNORADOS for parte in caminho.parts):
            continue
        if caminho.is_dir():
            locais.add(caminho.name)
        elif caminho.suffix == ".py":
            locais.add(caminho.stem)
    return locais


def _coletar_imports(coder_dir: Path) -> list[tuple[str, Path, int]]:
    """Extrai (módulo_raiz, arquivo, linha) de todo `.py` sob `coder_dir`.

    Imports relativos (`from .x import y`) são ignorados: são sempre locais.
    Arquivo com sintaxe inválida é pulado sem levantar exceção — o objetivo é
    coletar evidência, não validar o código.
    """
    achados: list[tuple[str, Path, int]] = []

    for arquivo in sorted(coder_dir.rglob("*.py")):
        if any(parte in _DIRS_IGNORADOS for parte in arquivo.parts):
            continue
        try:
            arvore = ast.parse(arquivo.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError, ValueError, OSError:
            continue

        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                for alias in no.names:
                    achados.append((alias.name.split(".")[0], arquivo, no.lineno))
            elif isinstance(no, ast.ImportFrom):
                if no.level or not no.module:
                    continue  # `from . import x` / `from .mod import y`
                achados.append((no.module.split(".")[0], arquivo, no.lineno))

    return achados


def verificar_dependencias(coder_dir: Path) -> list[dict]:
    """Imports de terceiros sem linha correspondente no requirements.txt.

    Args:
        coder_dir: Raiz do workspace do coder (onde vivem os `.py` e o requirements).

    Returns:
        Lista de achados, cada um com as chaves:

        - ``tipo``: ``"requirements_ausente"``, ``"import_nao_declarado"`` ou
          ``"import_transitivo"``
        - ``modulo``: nome do módulo raiz importado (``""`` no caso de ausência)
        - ``arquivo``: caminho relativo a ``coder_dir`` (``None`` se não aplicável)
        - ``linha``: linha do import (``None`` se não aplicável)
        - ``pacote_sugerido``: nome PyPI provável, quando conhecido
        - ``severidade``: ``"critical"`` ou ``"info"`` (ver D9 no módulo)
        - ``mensagem``: descrição legível do achado

        Achado ``import_transitivo`` é evidência, não pendência: ao contar
        divergências acionáveis, filtre por ``tipo``, não pelo tamanho da lista.

        Lista vazia significa "nada a reportar" — nunca significa aprovação. Este
        módulo descreve; quem julga é o `implementation_validator`.
    """
    if not coder_dir.is_dir():
        return []

    imports = _coletar_imports(coder_dir)
    if not imports:
        return []

    stdlib = sys.stdlib_module_names
    locais = _nomes_locais(coder_dir)
    req_path, declarados = _ler_requirements(coder_dir)

    # Primeira ocorrência de cada módulo de terceiros, em ordem estável.
    terceiros: dict[str, tuple[Path, int]] = {}
    for modulo, arquivo, linha in imports:
        if modulo in stdlib or modulo in locais or modulo in terceiros:
            continue
        terceiros[modulo] = (arquivo, linha)

    if not terceiros:
        return []

    # --- Caso inequívoco (D9: único que reprova) -----------------------------
    if req_path is None:
        modulos = sorted(terceiros)
        return [
            {
                "tipo": "requirements_ausente",
                "modulo": "",
                "arquivo": None,
                "linha": None,
                "pacote_sugerido": None,
                "severidade": "critical",
                "mensagem": (
                    f"Nenhum requirements.txt encontrado, mas o código importa "
                    f"{len(modulos)} módulo(s) de terceiros: {', '.join(modulos)}. "
                    f"O build da imagem falhará por dependência ausente."
                ),
            }
        ]

    # --- Divergências de nome (D9: informam, não reprovam) -------------------
    achados: list[dict] = []
    transitivos = _transitivos_disponiveis(declarados)

    for modulo in sorted(terceiros):
        arquivo, linha = terceiros[modulo]
        arquivo_rel = str(arquivo.relative_to(coder_dir)).replace("\\", "/")
        pacote = ALIAS_IMPORT_PARA_PACOTE.get(modulo, modulo)
        if _normalizar(pacote) in declarados or _normalizar(modulo) in declarados:
            continue

        provedor = transitivos.get(modulo)
        if provedor is not None:
            achados.append(
                {
                    "tipo": "import_transitivo",
                    "modulo": modulo,
                    "arquivo": arquivo_rel,
                    "linha": linha,
                    "pacote_sugerido": None,
                    "severidade": "info",
                    "mensagem": (
                        f"'import {modulo}' não consta em {req_path.name}, mas vem "
                        f"instalado com '{provedor}', que está declarado. Não requer "
                        f"ação: declarar uma dependência transitiva duplica o pin e "
                        f"pode conflitar com a faixa de versão que '{provedor}' exige."
                    ),
                }
            )
            continue

        conhecido = modulo in ALIAS_IMPORT_PARA_PACOTE
        achados.append(
            {
                "tipo": "import_nao_declarado",
                "modulo": modulo,
                "arquivo": arquivo_rel,
                "linha": linha,
                "pacote_sugerido": pacote if conhecido else None,
                "severidade": "info",
                "mensagem": (
                    f"'import {modulo}' sem linha correspondente em {req_path.name}"
                    + (
                        f" (o pacote PyPI de '{modulo}' chama-se '{pacote}')."
                        if conhecido
                        else ". Pode ser divergência entre nome de import e nome de "
                        "pacote — confirme antes de alterar."
                    )
                ),
            }
        )

    return achados
