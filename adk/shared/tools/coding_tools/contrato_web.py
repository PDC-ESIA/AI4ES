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


class Navegacao(BaseModel):
    """Aresta do mapa de navegação do design: origem → ação → destino."""

    origem: str = Field(description="id da tela de origem")
    acao: str = ""
    elemento: str = Field(description="testid do link/botão na tela de origem")
    dentro_de: Optional[str] = Field(
        default=None, description="testid do item de lista que contém o elemento (ex.: item-ensaio)"
    )
    destino: str = Field(description="id da tela de destino")


class Estilo(BaseModel):
    """Design system do design (ex.: design/prototypes/global.css)."""

    origem: str
    url: str = "/static/global.css"


class ContratoWeb(BaseModel):
    telas: list[Tela]
    rotas: list[Rota] = Field(default_factory=list)
    navegacao: list[Navegacao] = Field(default_factory=list)
    estilo: Optional[Estilo] = None
    decisoes: list[str] = Field(default_factory=list, description="decisões de arquitetura do design")
    suposicoes: list[str] = Field(default_factory=list, description="suposições do gap analysis do design")
    convencoes: list[str] = Field(default_factory=list)


def marcador(tela_id: str) -> str:
    """testid do contêiner principal de cada tela: é por ele que se sabe em que
    tela o usuário está (teste de navegação gerado do contrato)."""
    return f"tela-{re.sub(r'[^a-z0-9]+', '-', tela_id.lower()).strip('-')}"


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
        if "?" in rota.caminho:
            erros.append(
                f"rota {metodo} {rota.caminho}: sem query string no caminho — a rota é "
                f"{rota.caminho.split('?')[0]}; descreva o parâmetro em `resposta`."
            )
        if (metodo, rota.caminho) in chaves:
            erros.append(f"rota {metodo} {rota.caminho} repetida.")
        chaves.add((metodo, rota.caminho))
        if rota.task and validas and rota.task not in validas:
            erros.append(f"rota {metodo} {rota.caminho}: task desconhecida {rota.task}.")
    if not any(t.rota == "/" for t in contrato.telas):
        erros.append("falta a tela inicial (rota '/'), de onde o usuário alcança as demais.")
    telas = {t.id: t for t in contrato.telas}
    for tela in contrato.telas:
        if marcador(tela.id) not in {el.testid for el in tela.elementos}:
            erros.append(
                f"tela {tela.id}: falta o elemento `{marcador(tela.id)}` (papel tela), o contêiner "
                "principal que identifica a tela."
            )
    for nav in contrato.navegacao:
        origem = telas.get(nav.origem)
        if origem is None or nav.destino not in telas:
            erros.append(f"navegação {nav.origem} → {nav.destino}: tela inexistente.")
            continue
        ids_origem = {el.testid for el in origem.elementos}
        if nav.elemento not in ids_origem:
            erros.append(f"navegação {nav.origem} → {nav.destino}: `{nav.elemento}` não é elemento da tela {nav.origem}.")
        if nav.dentro_de and nav.dentro_de not in ids_origem:
            erros.append(f"navegação {nav.origem} → {nav.destino}: `{nav.dentro_de}` não é elemento da tela {nav.origem}.")
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
    if contrato.navegacao:
        linhas += ["", "## Navegação (mapa do design — homologada por teste de navegador)"]
        for n in contrato.navegacao:
            onde = f" dentro de `{n.dentro_de}`" if n.dentro_de else ""
            linhas.append(f"- {n.origem} → {n.destino}: clicar `{n.elemento}`{onde} ({n.acao})")
    if contrato.estilo:
        linhas += [
            "",
            "## Design system",
            f"- Folha de estilo do design `{contrato.estilo.origem}`, servida em "
            f"`{contrato.estilo.url}` e referenciada por TODAS as telas; use as variáveis dela.",
        ]
    linhas += [
        "",
        "## Marcadores de tela",
        "- O contêiner principal de cada tela leva `data-testid=\"tela-<id>\"` "
        f"({', '.join(f'`{marcador(t.id)}`' for t in contrato.telas)}).",
    ]
    for titulo, itens in (
        ("Decisões de arquitetura do design", contrato.decisoes),
        ("Suposições do design (siga-as)", contrato.suposicoes),
        ("Convenções", contrato.convencoes),
    ):
        if itens:
            linhas += ["", f"## {titulo}", *[f"- {c}" for c in itens]]
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
        caminho_rota = caminho_rota.split("?")[0]
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


# ── Navegação: teste gerado do contrato (sem LLM) ──────────────────────────

ARQUIVO_NAVEGACAO = "tests/journey/test_navegacao_contrato.py"


def _papel(contrato: ContratoWeb, tela_id: str, testid: str) -> Optional[str]:
    tela = next((t for t in contrato.telas if t.id == tela_id), None)
    el = next((e for e in (tela.elementos if tela else []) if e.testid == testid), None)
    return el.papel if el else None


def arestas_por_link(contrato: ContratoWeb) -> list[Navegacao]:
    """Só as arestas que são navegação pura (link). As que dependem de enviar
    formulário (botão "criar álbum") são homologadas pelos testes das tasks."""
    return [n for n in contrato.navegacao if _papel(contrato, n.origem, n.elemento) == "link"]


def _caminhos_a_partir_da_inicial(contrato: ContratoWeb) -> dict[str, list[Navegacao]]:
    """Menor sequência de cliques em links de "/" até cada tela (BFS no mapa)."""
    inicial = next((t.id for t in contrato.telas if t.rota == "/"), None)
    if inicial is None:
        return {}
    caminhos: dict[str, list[Navegacao]] = {inicial: []}
    fila = [inicial]
    while fila:
        atual = fila.pop(0)
        for nav in arestas_por_link(contrato):
            if nav.origem == atual and nav.destino not in caminhos:
                caminhos[nav.destino] = caminhos[atual] + [nav]
                fila.append(nav.destino)
    return caminhos


def _passo(nav: Navegacao) -> list[str]:
    if nav.dentro_de:
        alvo = f'_dentro(page, "{nav.dentro_de}").get_by_test_id("{nav.elemento}")'
    else:
        alvo = f'page.get_by_test_id("{nav.elemento}")'
    return [
        f"    # {nav.origem} → {nav.destino}: {nav.acao}",
        f"    {alvo}.click()",
        f'    expect(page.get_by_test_id("{marcador(nav.destino)}")).to_be_visible()',
    ]


def gerar_teste_navegacao(contrato: ContratoWeb) -> tuple[str, list[str]]:
    """(código pytest-playwright, telas inalcançáveis a partir de "/").

    Um teste por aresta do mapa de navegação do design: parte de "/", chega à
    tela de origem pelo menor caminho e clica no elemento da aresta, conferindo
    o marcador da tela de destino. Arestas dentro de item de lista (abrir um
    ensaio) usam o primeiro item existente — sem item, o teste é pulado.
    """
    caminhos = _caminhos_a_partir_da_inicial(contrato)
    inicial = next((t.id for t in contrato.telas if t.rota == "/"), "inicial")
    linhas = [
        '"""Gerado pelo pipeline a partir do contrato de interface (mapa de navegação do design).',
        "",
        "Protegido: o coder não o edita. Homologa que o usuário vai de uma tela a outra",
        'clicando, como o design definiu."""',
        "import pytest",
        "from playwright.sync_api import Page, expect",
        "",
        "",
        "def _dentro(page, item):",
        "    itens = page.get_by_test_id(item)",
        "    if itens.count() == 0:",
        '        pytest.skip(f"sem `{item}` para navegar (nenhum dado criado ainda)")',
        "    return itens.first",
        "",
        "",
        "def test_navegacao_00_tela_inicial(page: Page):",
        '    page.goto("/")',
        f'    expect(page.get_by_test_id("{marcador(inicial)}")).to_be_visible()',
    ]
    for i, nav in enumerate(arestas_por_link(contrato), start=1):
        if nav.origem not in caminhos:
            continue
        nome = re.sub(r"[^a-z0-9]+", "_", f"{nav.origem}_{nav.destino}".lower()).strip("_")
        linhas += ["", "", f"def test_navegacao_{i:02d}_{nome}(page: Page):", '    page.goto("/")']
        for passo in caminhos[nav.origem] + [nav]:
            linhas += _passo(passo)
    inalcancaveis = sorted(t.id for t in contrato.telas if t.id not in caminhos)
    return "\n".join(linhas) + "\n", inalcancaveis


# ── Conformidade com o design (só anota, nunca reprova) ────────────────────


def conformidade(
    contrato: ContratoWeb,
    workdir: Path,
    *,
    rotas_do_codigo: Optional[Iterable[tuple[str, str]]] = None,
    navegacao: Optional[dict] = None,
) -> dict:
    """Relatório determinístico de aderência da implementação ao design.

    Técnico: entra no relatório e no manifesto como nota, nunca reprova — o que
    o usuário percebe já é homologado pelos testes de interface e de navegação.
    """
    no_produto = ids_no_produto(workdir)
    elementos = testids(contrato)
    ausentes = [i for i in elementos if i not in no_produto]
    relatorio: dict = {
        "elementos_do_contrato": len(elementos),
        "elementos_ausentes": ausentes,
        "aderencia_elementos": round(1 - len(ausentes) / len(elementos), 3) if elementos else None,
        "telas_sem_marcador": [t.id for t in contrato.telas if marcador(t.id) not in no_produto],
    }
    if contrato.estilo:
        relatorio["estilo_referenciado"] = _referencia_estilo(workdir, contrato.estilo)
    if rotas_do_codigo is not None:
        relatorio["rotas_ausentes"] = rotas_divergentes(contrato, rotas_do_codigo)
    _, inalcancaveis = gerar_teste_navegacao(contrato)
    relatorio["telas_inalcancaveis_no_mapa"] = inalcancaveis
    if navegacao is not None:
        relatorio["navegacao"] = navegacao
    return relatorio


def _referencia_estilo(workdir: Path, estilo: Estilo) -> bool:
    nome = Path(estilo.url).name
    for p in Path(workdir).rglob("*"):
        rel = p.relative_to(workdir).parts
        if not p.is_file() or p.suffix not in (".html", ".jinja", ".jinja2", ".j2", ".jsx", ".tsx", ".vue", ".js", ".svelte"):
            continue
        if rel[:1] == ("tests",) or any(x in ("venv", ".venv", "node_modules") for x in rel):
            continue
        try:
            texto = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if estilo.url in texto or nome in texto:
            return True
    return False


def instalar_estilo_python_web(raiz_sessao: Path, workdir: Path, estilo: Optional[Estilo]) -> Optional[str]:
    """Copia o CSS do design para `static/` (trilha python-web); não sobrescreve."""
    if estilo is None:
        return None
    origem = Path(raiz_sessao) / estilo.origem
    destino = Path(workdir) / "static" / Path(estilo.url).name
    if not origem.is_file() or destino.exists():
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(origem.read_bytes())
    return destino.relative_to(workdir).as_posix()
