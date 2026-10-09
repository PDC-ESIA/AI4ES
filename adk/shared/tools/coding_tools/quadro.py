"""Quadro do produto (`AI4ES_QUADRO_PRODUTO`): o que as tasks anteriores entregaram.

O coder recebe só a task atual e a lista de arquivos herdados. Na 12ª validação
ele, corrigindo um detalhe da TASK-002, trocou o formato do identificador e
mexeu na criação do banco — e quebrou o que a TASK-001 entregara. O quadro dá a
visão do produto inteiro antes de cada task, para o foco ficar na big picture e
não só no problema imediato.

Montado de forma DETERMINÍSTICA (sem LLM, sem tokens de geração) pelo
TaskIterator no início de cada task, em duas camadas:

- genérica (qualquer stack): tasks fechadas com os critérios de homologação
  atendidos, testes protegidos que rodam como regressão, `data-testid` em uso
  e os arquivos do projeto;
- específica da trilha python-web: rotas (decorators FastAPI/Flask e `mount`
  de estáticos), modelos, templates e convenções (helper de identificador),
  extraídos com `ast` — sem importar o código do projeto.

Inspirado no "repo map" do Aider (mapa compacto do código num orçamento de
tokens), restrito ao que importa para não regredir.
"""

from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Optional

from shared.tools.coding_tools.aceite_independente import PASTA_ACEITE, ler_mapa
from shared.tools.coding_tools.criterios_aceite import normalizar_criterios
from shared.tools.coding_tools.jornada import PASTA_JORNADA, identificadores_existentes

logger = logging.getLogger(__name__)

# Teto do texto do quadro (~1,5–2 mil tokens).
LIMITE_CARACTERES = 7000
_IGNORADOS = {"venv", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ai4se_trilha"}
_METODOS_HTTP = {"get", "post", "put", "patch", "delete", "route", "api_route", "websocket"}
_ICONE = {"aprovado": "✔", "aceito_com_ressalvas": "≈", "reprovado": "✖"}


def _arquivos(workdir: Path, limite: int = 80) -> list[str]:
    arquivos: list[str] = []
    for caminho in sorted(workdir.rglob("*")):
        rel = caminho.relative_to(workdir)
        if not caminho.is_file() or any(p in _IGNORADOS or p.startswith(".") for p in rel.parts):
            continue
        if caminho.suffix in (".pyc", ".db", ".sqlite", ".sqlite3", ".jpg", ".jpeg", ".png", ".log"):
            continue
        arquivos.append(rel.as_posix())
        if len(arquivos) >= limite:
            break
    return arquivos


def _resultados_do_relatorio(report_path: Optional[str]) -> dict[str, str]:
    try:
        relatorio = json.loads(Path(report_path).read_text(encoding="utf-8")) if report_path else {}
    except (OSError, ValueError, TypeError):
        return {}
    return {
        e.get("criterion_id"): e.get("outcome")
        for e in relatorio.get("criteria_evidence") or []
        if isinstance(e, dict) and e.get("criterion_id")
    }


def _secao_tasks(tasks: Iterable[dict], task_results: dict) -> list[str]:
    linhas: list[str] = []
    for task in tasks:
        task_id = task.get("id")
        resultado = task_results.get(task_id)
        if not isinstance(resultado, dict):
            continue
        status = resultado.get("status", "?")
        linhas.append(f"- {_ICONE.get(status, '?')} {task_id} ({status}): {str(task.get('description', ''))[:110]}")
        desfechos = _resultados_do_relatorio(resultado.get("report_path"))
        for c in normalizar_criterios(task.get("acceptance_criteria")):
            if c.tecnico:
                continue
            marca = {"atendido": "✔", "nao_atendido": "✖"}.get(desfechos.get(c.id, ""), "·")
            linhas.append(f"    {marca} {c.id} {c.description[:120]}")
    return linhas


def _secao_regressao(workdir: Path, tasks_dir: Path, tasks: Iterable[dict], task_results: dict) -> list[str]:
    linhas: list[str] = []
    for task in tasks:
        task_id = task.get("id")
        if task_id not in task_results:
            continue
        mapa = ler_mapa(tasks_dir, task_id)
        for arquivo in (mapa or {}).get("arquivos") or []:
            if (workdir / arquivo).is_file():
                linhas.append(f"- {arquivo} ({task_id})")
    return linhas


# ── Camada python-web ──────────────────────────────────────────────────────


def _texto(no: ast.AST) -> Optional[str]:
    return no.value if isinstance(no, ast.Constant) and isinstance(no.value, str) else None


def _rotas_e_modelos(workdir: Path) -> tuple[list[str], list[str], list[str]]:
    rotas: list[str] = []
    estaticos: list[str] = []
    modelos: list[str] = []
    for caminho in sorted(workdir.rglob("*.py")):
        rel = caminho.relative_to(workdir)
        if any(p in _IGNORADOS for p in rel.parts) or rel.parts[0] == "tests":
            continue
        try:
            arvore = ast.parse(caminho.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for no in ast.walk(arvore):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in no.decorator_list:
                    if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)):
                        continue
                    metodo = dec.func.attr
                    caminho_rota = _texto(dec.args[0]) if dec.args else None
                    if metodo in _METODOS_HTTP and caminho_rota is not None:
                        verbo = metodo.upper() if metodo not in ("route", "api_route") else "ROUTE"
                        rotas.append(f"- {verbo} {caminho_rota} → {rel.as_posix()}:{no.name}")
            elif (
                isinstance(no, ast.Call)
                and isinstance(no.func, ast.Attribute)
                and no.func.attr == "mount"
                and no.args
                and _texto(no.args[0])
            ):
                estaticos.append(f"- {_texto(no.args[0])} ({rel.as_posix()})")
            elif isinstance(no, ast.ClassDef):
                atribuidos = [
                    alvo.id
                    for item in no.body
                    if isinstance(item, (ast.Assign, ast.AnnAssign))
                    for alvo in ([item.target] if isinstance(item, ast.AnnAssign) else item.targets)
                    if isinstance(alvo, ast.Name)
                ]
                if "__tablename__" in atribuidos:  # modelo SQLAlchemy
                    campos = [c for c in atribuidos if not c.startswith("_")][:12]
                    modelos.append(f"- {no.name} ({rel.as_posix()}): {', '.join(campos)}")
    return rotas, estaticos, modelos


def _rotas_do_contrato_ausentes(tasks_dir: Path, rotas: list[str]) -> list[str]:
    from shared.tools.coding_tools import contrato_web

    contrato = contrato_web.ler(tasks_dir)
    if contrato is None:
        return []
    no_codigo = []
    for linha in rotas:  # "- GET /x → arquivo:func"
        partes = linha[2:].split(" ", 2)
        if len(partes) >= 2:
            no_codigo.append((partes[0], partes[1]))
    return [f"- {r}" for r in contrato_web.rotas_divergentes(contrato, no_codigo)]


def _convencoes_python_web(workdir: Path) -> list[str]:
    linhas = []
    ids = workdir / "app" / "ids.py"
    if ids.is_file():
        linhas.append("- identificadores: `app/ids.py` (`novo_id()`); não gere id de outro jeito")
    templating = workdir / "app" / "templating.py"
    if templating.is_file():
        linhas.append("- templates: `app/templating.py` (Jinja2Templates)")
    return linhas


def _templates(workdir: Path, limite: int = 40) -> list[str]:
    return [
        f"- {p.relative_to(workdir).as_posix()}"
        for p in sorted(workdir.rglob("*.html"))
        if not any(parte in _IGNORADOS for parte in p.relative_to(workdir).parts)
    ][:limite]


# ── Montagem ───────────────────────────────────────────────────────────────


def montar_quadro(
    *,
    workdir: Path,
    tasks_dir: Path,
    tasks: list[dict],
    task_results: dict,
    trilha: Optional[dict],
    product_type: Any = None,
) -> str:
    """Texto do quadro (markdown curto); vazio antes da primeira task fechada."""
    if not task_results:
        return ""
    secoes: list[tuple[str, list[str]]] = [
        ("Tasks já fechadas e o que o usuário homologou", _secao_tasks(tasks, task_results)),
        (
            "Testes protegidos que rodam como regressão a cada rodada (não os quebre)",
            _secao_regressao(workdir, tasks_dir, tasks, task_results),
        ),
    ]
    ids = identificadores_existentes(workdir)
    if ids:
        secoes.append(("`data-testid` em uso (não renomeie nem reutilize)", [", ".join(ids)]))
    if trilha and trilha.get("id") == "python-web":
        rotas, estaticos, modelos = _rotas_e_modelos(workdir)
        divergentes = _rotas_do_contrato_ausentes(tasks_dir, rotas)
        if divergentes:
            secoes.append(("Rotas do contrato de interface ainda ausentes no código", divergentes))
        secoes += [
            ("Rotas existentes", rotas),
            ("Arquivos estáticos/mídia servidos", estaticos),
            ("Modelos (tabelas)", modelos),
            ("Templates", _templates(workdir)),
            ("Convenções adotadas", _convencoes_python_web(workdir)),
        ]
    secoes.append(("Arquivos do projeto", [", ".join(_arquivos(workdir))]))

    corpo = "\n\n".join(
        f"## {titulo}\n" + "\n".join(linhas) for titulo, linhas in secoes if linhas and any(linhas)
    )
    if len(corpo) > LIMITE_CARACTERES:
        corpo = corpo[:LIMITE_CARACTERES] + "\n… (quadro truncado)"
    return corpo


def secao_prompt(quadro: Optional[str]) -> str:
    """Seção do prompt (coder e autor de aceite); vazia sem quadro."""
    if not quadro:
        return ""
    return (
        "# O QUE JÁ EXISTE NO PRODUTO — NÃO QUEBRE\n"
        "Visão do produto construído pelas tasks anteriores (gerada do código e dos "
        "testes, não de memória). Implemente a task atual SEM alterar o que já foi "
        "homologado: reuse rotas, modelos, telas, identificadores e convenções "
        "existentes; mude contrato existente só se a task atual exigir — e então "
        "mantenha os testes protegidos passando.\n\n"
        f"{quadro}\n\n"
    )
