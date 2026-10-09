"""Contrato de interface de produto web (`AI4ES_CONTRATO_WEB`): top-down.

Nas validações, cada agente decidia sozinho uma parte da interface: o coder as
rotas (`/gallery` numa task, `/photos` noutra), cada autor de teste os seus
`data-testid` (`ensaios-titulo` × `campo-titulo-ensaio`) — e as tasks
travavam por contratos incompatíveis, não por defeito do produto. O design já
define componentes, rotas (diagramas de sequência) e telas (protótipos HTML);
faltava fixar isso ANTES do código.

Uma vez por execução, antes da primeira task, um agente (`cr_contract_author`)
deriva do design o contrato: telas com os seus elementos e `data-testid`,
rotas com método, formato e campos, e a task dona de cada parte. Este módulo é
a parte determinística — schema, validação, persistência e as checagens que
dependem dele:

- web_app, QUALQUER stack: o contrato, a seção dele no prompt do coder e do
  autor de aceite, testes presos aos identificadores do contrato e a lista de
  identificadores exigidos pelos testes que faltam no código;
- web_app na trilha python-web: além disso, o esqueleto (`app/ids.py`) e a
  conferência das rotas do código com as do contrato (via `ast`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, Field, ValidationError

from shared.tools.coding_tools.jornada import identificador_equivalente

ARQUIVO_CONTRATO = "_contrato_web.json"
_TESTID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_METODOS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_FORMATOS = {"form", "multipart", "json", "nenhum"}


class Elemento(BaseModel):
    testid: str = Field(description="data-testid, kebab-case, único no contrato")
    papel: str = Field(description="form | campo | botao | link | lista | item | texto | imagem | outro")
    descricao: str = ""
    task: Optional[str] = None


class Tela(BaseModel):
    id: str
    titulo: str = ""
    rota: str = Field(description="Rota GET que exibe a tela, ex.: /ensaios/{ensaio_id}")
    prototipo: Optional[str] = None
    tasks: list[str] = Field(default_factory=list)
    elementos: list[Elemento] = Field(default_factory=list)


class Rota(BaseModel):
    metodo: str
    caminho: str
    formato: str = "nenhum"
    campos: list[str] = Field(default_factory=list)
    resposta: str = ""
    task: Optional[str] = None


class ContratoWeb(BaseModel):
    telas: list[Tela]
    rotas: list[Rota] = Field(default_factory=list)
    convencoes: list[str] = Field(default_factory=list)


# ── Validação ──────────────────────────────────────────────────────────────


def validar(dados: object, task_ids: Iterable[str] = ()) -> tuple[Optional[ContratoWeb], list[str]]:
    """(contrato, erros). Erros deterministas que o autor corrige e salva de novo."""
    try:
        contrato = ContratoWeb.model_validate(dados)
    except ValidationError as exc:
        return None, [f"formato inválido: {e['loc']}: {e['msg']}" for e in exc.errors()][:10]
    erros: list[str] = []
    validas = set(task_ids)
    vistos: list[str] = []
    for tela in contrato.telas:
        if not tela.rota.startswith("/"):
            erros.append(f"tela {tela.id}: rota deve começar com '/'.")
        for t in tela.tasks:
            if validas and t not in validas:
                erros.append(f"tela {tela.id}: task desconhecida {t}.")
        for el in tela.elementos:
            if not _TESTID_RE.match(el.testid):
                erros.append(f"`{el.testid}`: use kebab-case minúsculo (ex.: btn-criar-ensaio).")
            if el.testid in vistos:
                erros.append(f"`{el.testid}` repetido: cada elemento tem um identificador único.")
            elif (igual := identificador_equivalente(el.testid, vistos)) is not None:
                erros.append(f"`{el.testid}` equivale a `{igual}`: um nome por elemento.")
            vistos.append(el.testid)
    chaves = set()
    for rota in contrato.rotas:
        metodo = rota.metodo.upper()
        if metodo not in _METODOS:
            erros.append(f"rota {rota.caminho}: método {rota.metodo} inválido.")
        if rota.formato not in _FORMATOS:
            erros.append(f"rota {metodo} {rota.caminho}: formato deve ser um de {sorted(_FORMATOS)}.")
        if (metodo, rota.caminho) in chaves:
            erros.append(f"rota {metodo} {rota.caminho} repetida.")
        chaves.add((metodo, rota.caminho))
        if rota.task and validas and rota.task not in validas:
            erros.append(f"rota {metodo} {rota.caminho}: task desconhecida {rota.task}.")
    if not any(t.rota == "/" for t in contrato.telas):
        erros.append("falta a tela inicial (rota '/'), de onde o usuário alcança as demais.")
    return (contrato if not erros else None), erros


# ── Persistência ───────────────────────────────────────────────────────────


def caminho(tasks_dir: Path) -> Path:
    return Path(tasks_dir) / ARQUIVO_CONTRATO


def gravar(tasks_dir: Path, contrato: ContratoWeb) -> Path:
    destino = caminho(tasks_dir)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contrato.model_dump_json(indent=2), encoding="utf-8")
    return destino


def ler(tasks_dir: Path) -> Optional[ContratoWeb]:
    try:
        return ContratoWeb.model_validate_json(caminho(tasks_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def testids(contrato: Optional[ContratoWeb]) -> list[str]:
    if contrato is None:
        return []
    return [el.testid for tela in contrato.telas for el in tela.elementos]


# ── Prompt ─────────────────────────────────────────────────────────────────


def _linhas_tela(tela: Tela, *, detalhar: bool) -> list[str]:
    cab = f"- Tela `{tela.id}` em GET {tela.rota}"
    if tela.prototipo:
        cab += f" (protótipo: {tela.prototipo})"
    if tela.tasks:
        cab += f" — tasks {', '.join(tela.tasks)}"
    linhas = [cab]
    if detalhar:
        linhas += [
            f"    - `{el.testid}` ({el.papel}){': ' + el.descricao if el.descricao else ''}"
            for el in tela.elementos
        ]
    return linhas


def secao_prompt(contrato: Optional[ContratoWeb], task_id: Optional[str]) -> str:
    """Seção do prompt: o contrato inteiro em resumo, detalhado no que é da task."""
    if contrato is None:
        return ""
    linhas = [
        "# CONTRATO DE INTERFACE DO PRODUTO (FIXO — vem do design)",
        "Telas, elementos e rotas já decididos para o produto inteiro. Implemente "
        "a sua parte EXATAMENTE assim: mesmos caminhos de rota, mesmos campos e "
        "formatos, e cada elemento com o `data-testid` indicado — os testes de "
        "homologação usam esses identificadores. Não crie identificador nem rota "
        "fora do contrato para funcionalidade que o contrato já cobre, e não "
        "altere a parte de outras tasks (só acrescente links/navegação).",
        "",
        "## Telas",
    ]
    for tela in contrato.telas:
        detalhar = task_id is None or task_id in tela.tasks or any(
            el.task == task_id for el in tela.elementos
        )
        linhas += _linhas_tela(tela, detalhar=detalhar)
    if contrato.rotas:
        linhas += ["", "## Rotas"]
        for r in contrato.rotas:
            campos = f" campos: {', '.join(r.campos)}" if r.campos else ""
            dono = f" [{r.task}]" if r.task else ""
            resposta = f" → {r.resposta}" if r.resposta else ""
            linhas.append(f"- {r.metodo.upper()} {r.caminho} ({r.formato}){campos}{resposta}{dono}")
    if contrato.convencoes:
        linhas += ["", "## Convenções", *[f"- {c}" for c in contrato.convencoes]]
    return "\n".join(linhas) + "\n\n"


# ── Checagens determinísticas ──────────────────────────────────────────────

_GET_BY_TEST_ID = re.compile(r"""get_by_test_id\(\s*["']([^"']+)["']""")


def identificadores_exigidos(workdir: Path, arquivos: Iterable[str]) -> set[str]:
    """`data-testid` que os testes protegidos procuram."""
    exigidos: set[str] = set()
    for arquivo in arquivos:
        try:
            exigidos.update(_GET_BY_TEST_ID.findall((Path(workdir) / arquivo).read_text(encoding="utf-8")))
        except OSError:
            continue
    return exigidos


def identificadores_ausentes(workdir: Path, arquivos_de_teste: Iterable[str]) -> list[str]:
    """Identificadores que os testes exigem e o código do produto não define.

    Qualquer stack web: varre HTML, templates, JS/TS/JSX/Vue/Svelte e Python,
    fora de `tests/`. Identificador montado em tempo de execução pode aparecer
    como falso ausente — por isso é dica para o coder, não bloqueio.
    """
    exigidos = identificadores_exigidos(workdir, arquivos_de_teste)
    return sorted(exigidos - ids_no_produto(workdir)) if exigidos else []


_DATA_TESTID = re.compile(r"""data-testid\s*=\s*\{?\s*["'`]([^"'`{}<>$]+)["'`]""")
_SUFIXOS_PRODUTO = (".html", ".jinja", ".jinja2", ".j2", ".js", ".jsx", ".ts", ".tsx", ".vue", ".py", ".svelte")


def ids_no_produto(workdir: Path) -> set[str]:
    encontrados: set[str] = set()
    for p in Path(workdir).rglob("*"):
        rel = p.relative_to(workdir).parts
        if not p.is_file() or p.suffix not in _SUFIXOS_PRODUTO:
            continue
        if rel[:1] == ("tests",) or any(x in ("venv", ".venv", "node_modules", "__pycache__") for x in rel):
            continue
        try:
            encontrados.update(_DATA_TESTID.findall(p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return encontrados


def rotas_divergentes(contrato: Optional[ContratoWeb], rotas_do_codigo: Iterable[tuple[str, str]]) -> list[str]:
    """Rotas do contrato que o código (trilha python-web) ainda não tem."""
    if contrato is None:
        return []

    def norm(caminho_rota: str) -> str:
        return re.sub(r"\{[^}]+\}", "{}", caminho_rota.rstrip("/") or "/")

    no_codigo = {(m.upper(), norm(c)) for m, c in rotas_do_codigo}
    faltam = []
    for r in contrato.rotas:
        if (r.metodo.upper(), norm(r.caminho)) not in no_codigo:
            faltam.append(f"{r.metodo.upper()} {r.caminho}" + (f" [{r.task}]" if r.task else ""))
    for tela in contrato.telas:
        if ("GET", norm(tela.rota)) not in no_codigo:
            faltam.append(f"GET {tela.rota} (tela {tela.id})")
    return sorted(set(faltam))


ESQUELETO_IDS = '''"""Gerado pelo pipeline (contrato de interface): o ÚNICO gerador de identificadores."""
import uuid


def novo_id() -> str:
    return str(uuid.uuid4())
'''


def instalar_esqueleto_python_web(workdir: Path) -> list[str]:
    """Arquivos de convenção da trilha python-web; não sobrescreve nada."""
    criados = []
    ids = Path(workdir) / "app" / "ids.py"
    if not ids.exists():
        ids.parent.mkdir(parents=True, exist_ok=True)
        init = ids.parent / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")
            criados.append("app/__init__.py")
        ids.write_text(ESQUELETO_IDS, encoding="utf-8")
        criados.append("app/ids.py")
    return criados


def contexto_autor(tasks: list[dict], macro: dict, artefatos_design: list[str]) -> str:
    """Entrada do `cr_contract_author`."""
    return json.dumps(
        {
            "product_type": macro.get("product_type"),
            "tech_stack": macro.get("tech_stack"),
            "tasks": [
                {
                    "id": t.get("id"),
                    "description": str(t.get("description", ""))[:400],
                    "criterios": [
                        c.get("description") for c in t.get("acceptance_criteria") or [] if isinstance(c, dict)
                    ],
                    "interfaces": (t.get("contract") or {}).get("interfaces"),
                }
                for t in tasks
            ],
            "artefatos_de_design": artefatos_design,
        },
        ensure_ascii=False,
        indent=2,
    )
