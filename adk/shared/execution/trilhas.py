"""Trilhas de execução: stacks conhecidas com interpretador e dependências fixados.

O ambiente do coder não é fixo — cada projeto escolhe a sua `tech_stack`. Mas
quando a stack cai numa TRILHA conhecida, o harness pode executá-la num
ambiente previsível em vez do `python3` que estiver no host. Na run do
fotógrafo o host tinha Python 3.14: `imghdr` (removido no 3.13) e um
`TestClient` sem `httpx` custaram iterações inteiras do coder, ~1 mi de tokens
cada, por diferenças de ambiente e não de lógica.

Uma trilha define:
- a versão do interpretador, resolvida no host (`python3.12` no PATH ou
  `uv python find`); sem ele, a trilha simplesmente não se aplica;
- um arquivo de restrições (`constraints/*.txt`) aplicado via `PIP_CONSTRAINT`,
  que o pip honra sem que o coder mude os comandos do `run.json`;
- notas para o prompt do coder com as armadilhas conhecidas da stack.

Stacks fora das trilhas continuam livres (comportamento histórico).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

_CONSTRAINTS_DIR = Path(__file__).resolve().parent / "constraints"

# Pasta, dentro da raiz do sandbox, com os atalhos `python3`/`python` que
# apontam para o interpretador da trilha.
PASTA_ATALHOS = ".ai4se_trilha"


@dataclass(frozen=True)
class Trilha:
    id: str
    python: str
    # Termos que identificam a stack; casam por substring, sem caixa.
    exige: frozenset[str]
    # Ao menos um destes também precisa aparecer (vazio = só `exige`).
    exige_algum: frozenset[str] = frozenset()
    constraints: Optional[str] = None
    notas: str = ""


_NOTAS_PYTHON = """- O harness executa os comandos do `run.json` com `python3` = Python {python}.
  Continue criando o venv com `python3 -m venv venv`.
- Declare as dependências SEM fixar versão (`fastapi`, não `fastapi==x`): o
  ambiente aplica restrições de versão testadas em conjunto.
- Módulos removidos da stdlib recente (`imghdr`, `cgi`, `distutils`) NÃO
  existem: detecte formato de imagem com Pillow (`Image.open(...).format`)."""

_NOTAS_PYTHON_WEB = (
    _NOTAS_PYTHON
    + """
- `fastapi.testclient.TestClient` exige o pacote `httpx` (não `httpx2`).
- `TemplateResponse(request, "nome.html", {{...}})` — request como 1º argumento.
- Formulário HTML (`<form method="post">`) envia `application/x-www-form-urlencoded`:
  o endpoint que o recebe usa `Form(...)`, não um modelo Pydantic no corpo.
- Arquivos enviados/gerados que a página exibe precisam de rota: monte
  `StaticFiles` no diretório e use URLs absolutas (`/media/...`) nos templates.
- Para não haver import circular, crie `Jinja2Templates` num módulo próprio
  (ex.: `app/templating.py`) e importe-o nas rotas — nunca de `app.main`.
- Testabilidade: leia o caminho do banco e das pastas de arquivos de variáveis
  de ambiente (`DATABASE_URL`, `MEDIA_DIR`), com padrão local — nada de
  caminho fixo no código. Crie as tabelas na inicialização da aplicação
  (lifespan) e não recrie engine/sessão em tempo de execução. Testes de
  aceite e de jornada, que você não edita, rodam em processo próprio e apontam
  essas variáveis para pastas temporárias.
- Caminhos citados nos requisitos e critérios (ex.:
  `/storage/ensaio/<id>/originals`) são RELATIVOS à pasta de arquivos
  configurada (`MEDIA_DIR`, com padrão local como `./media`): nunca grave na
  raiz do sistema. Os arquivos gravados precisam ser servidos (StaticFiles)
  pela mesma pasta.
- Sem configuração nenhuma, o produto tem de funcionar: o teste de jornada
  sobe a aplicação pelo `run` do `run.json` e a usa como o usuário."""
)

TRILHAS: tuple[Trilha, ...] = (
    Trilha(
        id="python-web",
        python="3.12",
        exige=frozenset({"python"}),
        exige_algum=frozenset({"fastapi", "flask", "starlette", "jinja"}),
        constraints="python-web-py312.txt",
        notas=_NOTAS_PYTHON_WEB,
    ),
    Trilha(
        id="python-generic",
        python="3.12",
        exige=frozenset({"python"}),
        notas=_NOTAS_PYTHON,
    ),
)


def _termos(tech_stack: Any) -> list[str]:
    if isinstance(tech_stack, str):
        itens: Iterable[Any] = [tech_stack]
    elif isinstance(tech_stack, (list, tuple)):
        itens = tech_stack
    else:
        return []
    return [str(t).strip().lower() for t in itens if str(t).strip()]


def _casa(trilha: Trilha, termos: list[str]) -> bool:
    texto = " ".join(termos)
    if not all(t in texto for t in trilha.exige):
        return False
    return not trilha.exige_algum or any(t in texto for t in trilha.exige_algum)


def resolver_interpretador(versao: str) -> Optional[str]:
    """Caminho absoluto de um Python `versao` no host, ou None.

    Ordem: variável `AI4ES_TRILHA_PYTHON_<versão sem ponto>` (ex.:
    `AI4ES_TRILHA_PYTHON_312`), `python<versão>` no PATH, `uv python find`.
    """
    sufixo = versao.replace(".", "")
    explicito = os.environ.get(f"AI4ES_TRILHA_PYTHON_{sufixo}", "").strip()
    if explicito:
        return explicito if Path(explicito).is_file() else None

    no_path = shutil.which(f"python{versao}")
    if no_path:
        return str(Path(no_path).resolve())

    uv = shutil.which("uv")
    if uv:
        try:
            proc = subprocess.run(
                [uv, "python", "find", "--no-project", versao],
                capture_output=True,
                text=True,
                timeout=20,
                cwd=str(Path.home()),
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        caminho = (proc.stdout or "").strip().splitlines()
        if proc.returncode == 0 and caminho and Path(caminho[-1]).is_file():
            return caminho[-1]
    return None


def selecionar_trilha(tech_stack: Any) -> Optional[dict]:
    """Primeira trilha que casa com a stack E tem interpretador no host.

    Devolve um dict serializável (vai para o state da sessão), ou None quando a
    stack é livre.
    """
    termos = _termos(tech_stack)
    if not termos:
        return None
    for trilha in TRILHAS:
        if not _casa(trilha, termos):
            continue
        interpretador = resolver_interpretador(trilha.python)
        if interpretador is None:
            continue
        constraints = (
            str(_CONSTRAINTS_DIR / trilha.constraints) if trilha.constraints else None
        )
        return {
            "id": trilha.id,
            "python": trilha.python,
            "interpretador": interpretador,
            "constraints": constraints,
            "notas": trilha.notas.format(python=trilha.python),
        }
    return None


def ambiente_da_trilha(trilha: Optional[dict], raiz: Path) -> dict[str, str]:
    """Variáveis de ambiente que colocam os comandos do `run.json` na trilha.

    Cria `raiz/.ai4se_trilha/bin` com `python3`/`python` apontando para o
    interpretador e o põe à frente do PATH; aplica as restrições via
    `PIP_CONSTRAINT`. Trilha ausente ou inválida → `{}` (ambiente histórico).
    """
    if not isinstance(trilha, dict):
        return {}
    interpretador = trilha.get("interpretador")
    if not isinstance(interpretador, str) or not Path(interpretador).is_file():
        return {}

    pasta = raiz / PASTA_ATALHOS / "bin"
    pasta.mkdir(parents=True, exist_ok=True)
    versao = str(trilha.get("python") or "")
    for nome in sorted({"python3", "python", f"python{versao}"}):
        atalho = pasta / nome
        if atalho.is_symlink() or atalho.exists():
            atalho.unlink()
        atalho.symlink_to(interpretador)

    env = {"PATH": f"{pasta}{os.pathsep}{os.environ.get('PATH', '')}"}
    constraints = trilha.get("constraints")
    if isinstance(constraints, str) and Path(constraints).is_file():
        env["PIP_CONSTRAINT"] = constraints
    return env


def secao_prompt(trilha: Optional[dict]) -> str:
    """Seção da instrução do coder para a trilha (vazia sem trilha)."""
    if not isinstance(trilha, dict) or not trilha.get("id"):
        return ""
    return (
        f"# TRILHA DE EXECUÇÃO: {trilha['id']} (Python {trilha.get('python', '?')})\n\n"
        "Sua stack caiu numa trilha conhecida; o ambiente do harness é fixo:\n"
        f"{trilha.get('notas', '')}\n\n"
    )
