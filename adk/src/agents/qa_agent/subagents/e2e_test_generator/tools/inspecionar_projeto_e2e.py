"""Inspeção determinística e somente-leitura de projetos candidatos a E2E."""

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from shared.workspace import get_workspace_root

from ..schemas import (
    ContratoAPIDescobertoE2E,
    EntradaE2ENormalizada,
    ProjetoInspecionadoE2E,
    RotaDescobertaE2E,
    TipoSistema,
)

_RAIZ_ADK = Path(__file__).resolve().parents[6]
_MAX_ARQUIVOS = 200
_MAX_BYTES_ARQUIVO = 200_000
_MAX_BYTES_TOTAL = 1_000_000
_EXTENSOES_TEXTO = {
    ".htm",
    ".html",
    ".js",
    ".jsx",
    ".json",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
_DIRETORIOS_IGNORADOS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "dist",
    "node_modules",
    "playwright-report",
    "test-results",
}
_LINGUAGENS = {
    ".html": "html",
    ".htm": "html",
    ".js": "javascript",
    ".jsx": "javascript",
    ".json": "json",
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
}


@dataclass(frozen=True)
class _ArquivoInspecao:
    nome: str
    conteudo: str


def _contratos_fastapi_literais(
    nome: str,
    conteudo: str,
) -> list[ContratoAPIDescobertoE2E]:
    """Extrai somente decoradores e retornos literais, sem importar o projeto."""

    try:
        arvore = ast.parse(conteudo)
    except SyntaxError:
        return []

    contratos: list[ContratoAPIDescobertoE2E] = []
    metodos = {"get", "post", "put", "patch", "delete", "options", "head"}
    for no in arvore.body:
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        retornos = [
            filho
            for filho in no.body
            if isinstance(filho, ast.Return) and filho.value is not None
        ]
        resposta_disponivel = len(retornos) == 1
        resposta_esperada = None
        if resposta_disponivel:
            try:
                resposta_esperada = ast.literal_eval(retornos[0].value)
            except (TypeError, ValueError):
                resposta_disponivel = False

        for decorador in no.decorator_list:
            if (
                not isinstance(decorador, ast.Call)
                or not isinstance(decorador.func, ast.Attribute)
                or decorador.func.attr.lower() not in metodos
                or not decorador.args
                or not isinstance(decorador.args[0], ast.Constant)
                or not isinstance(decorador.args[0].value, str)
            ):
                continue
            rota = decorador.args[0].value
            if not rota.startswith("/"):
                continue
            status = 200
            status_observavel = True
            for argumento in decorador.keywords:
                if argumento.arg == "status_code":
                    try:
                        valor = ast.literal_eval(argumento.value)
                    except (TypeError, ValueError):
                        status_observavel = False
                        break
                    if isinstance(valor, int) and 100 <= valor <= 599:
                        status = valor
                    else:
                        status_observavel = False
                    break
            if not status_observavel:
                continue
            contratos.append(
                ContratoAPIDescobertoE2E(
                    rota=rota,
                    metodo=decorador.func.attr.upper(),
                    status_esperado=status,
                    resposta_esperada=(
                        resposta_esperada if resposta_disponivel else None
                    ),
                    origem=f"{nome}:{getattr(no, 'lineno', 1)}",
                    confianca=0.95 if resposta_disponivel else 0.8,
                )
            )
    return contratos


def _esta_contido(caminho: Path, raiz: Path) -> bool:
    try:
        caminho.relative_to(raiz)
        return True
    except ValueError:
        return False


def _resolver_workspace(workspace_projeto: str) -> tuple[Path | None, str | None]:
    candidato = Path(workspace_projeto).expanduser()
    if not candidato.is_absolute():
        candidato = _RAIZ_ADK / candidato
    candidato = candidato.resolve()
    raizes_permitidas = {_RAIZ_ADK.resolve(), get_workspace_root().resolve()}
    if not any(_esta_contido(candidato, raiz) for raiz in raizes_permitidas):
        return None, (
            "workspace_projeto deve estar dentro do projeto ADK ou do workspace "
            "gerenciado dos agentes."
        )
    if not candidato.exists():
        return None, f"workspace_projeto não existe: {candidato}"
    if not candidato.is_dir():
        return None, "workspace_projeto deve apontar para um diretório."
    return candidato, None


def _arquivos_do_workspace(
    workspace_projeto: str | None,
) -> tuple[list[_ArquivoInspecao], list[str], list[str]]:
    if not workspace_projeto:
        return [], [], []
    raiz, erro = _resolver_workspace(workspace_projeto)
    if erro or raiz is None:
        return [], [], [erro or "workspace_projeto inválido."]

    arquivos: list[_ArquivoInspecao] = []
    limites: list[str] = []
    total_bytes = 0
    for caminho in raiz.rglob("*"):
        if not caminho.is_file():
            continue
        relativo = caminho.relative_to(raiz)
        if any(parte.lower() in _DIRETORIOS_IGNORADOS for parte in relativo.parts):
            continue
        if caminho.suffix.lower() not in _EXTENSOES_TEXTO:
            continue
        if len(arquivos) >= _MAX_ARQUIVOS:
            limites.append(f"limite de {_MAX_ARQUIVOS} arquivos atingido")
            break
        try:
            resolvido = caminho.resolve()
            if not _esta_contido(resolvido, raiz):
                continue
            tamanho = resolvido.stat().st_size
            if tamanho > _MAX_BYTES_ARQUIVO:
                limites.append(f"arquivo ignorado por tamanho: {relativo.as_posix()}")
                continue
            if total_bytes + tamanho > _MAX_BYTES_TOTAL:
                limites.append(f"limite total de {_MAX_BYTES_TOTAL} bytes atingido")
                break
            conteudo = resolvido.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        arquivos.append(_ArquivoInspecao(relativo.as_posix(), conteudo))
        total_bytes += tamanho
    return arquivos, list(dict.fromkeys(limites)), []


def _modulo_python(nome: str) -> str | None:
    caminho = PurePosixPath(nome.replace("\\", "/"))
    if caminho.suffix.lower() != ".py":
        return None
    partes = list(caminho.with_suffix("").parts)
    if partes and partes[0] == "src":
        partes = partes[1:]
    if not partes or not all(re.fullmatch(r"[A-Za-z_]\w*", parte) for parte in partes):
        return None
    return ".".join(partes)


def _rota_html(nome: str) -> str | None:
    caminho = PurePosixPath(nome.replace("\\", "/"))
    if caminho.suffix.lower() not in {".html", ".htm"}:
        return None
    partes = list(caminho.with_suffix("").parts)
    if partes and partes[0].lower() in {"public", "static"}:
        partes = partes[1:]
    if partes and partes[-1].lower() == "index":
        partes = partes[:-1]
    return "/" + "/".join(partes) if partes else "/"


def _rota_next(nome: str) -> str | None:
    caminho = PurePosixPath(nome.replace("\\", "/"))
    partes = list(caminho.parts)
    if "app" in partes and caminho.stem == "page":
        partes = partes[partes.index("app") + 1 : -1]
    elif "pages" in partes and caminho.suffix.lower() in {".js", ".jsx", ".ts", ".tsx"}:
        partes = partes[partes.index("pages") + 1 :]
        partes[-1] = caminho.stem
        if partes[-1] == "index":
            partes = partes[:-1]
    else:
        return None
    partes = [parte for parte in partes if not (parte.startswith("(") and parte.endswith(")"))]
    return "/" + "/".join(partes) if partes else "/"


def _inspecionar_arquivos(
    arquivos: list[_ArquivoInspecao],
    limites: list[str],
    bloqueios: list[str],
) -> ProjetoInspecionadoE2E:
    pontos: dict[str, int] = {}
    sinais: list[str] = []
    linguagens: list[str] = []
    rotas: list[RotaDescobertaE2E] = []
    contratos_api: list[ContratoAPIDescobertoE2E] = []
    entrypoints: dict[str, str] = {}
    scripts_npm: dict[str, str] = {}

    def pontuar(framework: str, valor: int, sinal: str) -> None:
        pontos[framework] = max(pontos.get(framework, 0), valor)
        sinais.append(sinal)

    def adicionar_rota(rota: str, origem: str, metodo: str | None = None) -> None:
        rota = rota.strip()
        if not rota or not rota.startswith("/"):
            return
        rotas.append(RotaDescobertaE2E(rota=rota, metodo=metodo, origem=origem))

    for arquivo in arquivos:
        nome = arquivo.nome
        conteudo = arquivo.conteudo
        sufixo = PurePosixPath(nome.replace("\\", "/")).suffix.lower()
        linguagem = _LINGUAGENS.get(sufixo)
        if linguagem:
            linguagens.append(linguagem)

        if PurePosixPath(nome).name == "package.json":
            try:
                pacote = json.loads(conteudo)
            except json.JSONDecodeError:
                pacote = {}
            dependencies = pacote.get("dependencies", {})
            dev_dependencies = pacote.get("devDependencies", {})
            dependencias = {
                **(dependencies if isinstance(dependencies, dict) else {}),
                **(dev_dependencies if isinstance(dev_dependencies, dict) else {}),
            }
            scripts = pacote.get("scripts", {})
            if isinstance(scripts, dict):
                scripts_npm.update(
                    {str(chave): str(valor) for chave, valor in scripts.items()}
                )
            if "next" in dependencias:
                pontuar("nextjs", 5, f"Next.js declarado em {nome}")
            if "vite" in dependencias:
                pontuar("vite", 4, f"Vite declarado em {nome}")
            if "react" in dependencias:
                pontuar("react", 2, f"React declarado em {nome}")
            if "express" in dependencias:
                pontuar("express", 4, f"Express declarado em {nome}")
            principal = pacote.get("main")
            if isinstance(principal, str) and principal:
                entrypoints["express"] = principal

        modulo = _modulo_python(nome)
        fastapi = re.search(r"(?P<app>\w+)\s*=\s*FastAPI\s*\(", conteudo)
        flask = re.search(r"(?P<app>\w+)\s*=\s*Flask\s*\(", conteudo)
        if fastapi:
            pontuar("fastapi", 5, f"FastAPI inicializado em {nome}")
            if modulo:
                entrypoints["fastapi"] = f"{modulo}:{fastapi.group('app')}"
            contratos_api.extend(_contratos_fastapi_literais(nome, conteudo))
        if flask:
            pontuar("flask", 5, f"Flask inicializado em {nome}")
            if modulo:
                entrypoints["flask"] = f"{modulo}:{flask.group('app')}"
        if PurePosixPath(nome).name == "manage.py":
            pontuar("django", 5, f"manage.py encontrado em {nome}")
            entrypoints["django"] = nome
        if "urlpatterns" in conteudo and re.search(r"\b(?:path|re_path)\s*\(", conteudo):
            pontuar("django", 3, f"urlpatterns encontrado em {nome}")

        for correspondencia in re.finditer(
            r"@\w+\.(?P<method>get|post|put|patch|delete|options|head|route)"
            r"\s*\(\s*[\"'](?P<route>/[^\"']*)[\"']",
            conteudo,
            flags=re.IGNORECASE,
        ):
            metodo = correspondencia.group("method").upper()
            adicionar_rota(
                correspondencia.group("route"),
                nome,
                None if metodo == "ROUTE" else metodo,
            )
        for correspondencia in re.finditer(
            r"\b(?:path|re_path)\s*\(\s*[\"'](?P<route>[^\"']*)[\"']",
            conteudo,
        ):
            adicionar_rota("/" + correspondencia.group("route").lstrip("/"), nome)

        if re.search(r"\b(?:const|let|var)\s+\w+\s*=\s*express\s*\(", conteudo):
            pontuar("express", 4, f"Express inicializado em {nome}")
            entrypoints.setdefault("express", nome)
        for correspondencia in re.finditer(
            r"\b(?:app|router)\.(?P<method>get|post|put|patch|delete|options|head)"
            r"\s*\(\s*[\"'`](?P<route>/[^\"'`]*)[\"'`]",
            conteudo,
            flags=re.IGNORECASE,
        ):
            adicionar_rota(
                correspondencia.group("route"),
                nome,
                correspondencia.group("method").upper(),
            )
        for correspondencia in re.finditer(
            r"(?:\bpath\s*[:=]|<Route[^>]*\bpath=)\s*[\"'`](?P<route>/[^\"'`]*)[\"'`]",
            conteudo,
        ):
            adicionar_rota(correspondencia.group("route"), nome)

        rota_next = _rota_next(nome)
        if rota_next is not None:
            pontuar("nextjs", 2, f"rota de arquivo Next.js encontrada em {nome}")
            adicionar_rota(rota_next, nome)
        rota_html = _rota_html(nome)
        if rota_html is not None:
            pontuar("html_estatico", 1, f"documento HTML encontrado em {nome}")
            adicionar_rota(rota_html, nome)
        if sufixo in {".jsx", ".tsx"} and ("from 'react'" in conteudo or 'from "react"' in conteudo):
            pontuar("react", 1, f"componente React encontrado em {nome}")

    framework = max(pontos, key=pontos.get) if pontos else "desconhecido"
    maior_pontuacao = pontos.get(framework, 0)
    if framework == "fastapi":
        tem_html = any("documento HTML" in sinal for sinal in sinais)
        tipo_sistema = TipoSistema.FULLSTACK if tem_html else TipoSistema.API
        perfil = "uvicorn"
        entrypoint = entrypoints.get(framework)
        comando = ["uvicorn", entrypoint] if entrypoint else []
    elif framework == "flask":
        tipo_sistema = TipoSistema.FULLSTACK
        perfil = "flask"
        entrypoint = entrypoints.get(framework)
        comando = ["flask", "--app", entrypoint, "run"] if entrypoint else []
    elif framework == "django":
        tipo_sistema = TipoSistema.FULLSTACK
        perfil = "django_runserver"
        entrypoint = entrypoints.get(framework)
        comando = ["python", entrypoint, "runserver"] if entrypoint else []
    elif framework in {"express", "nextjs", "vite", "react"}:
        tipo_sistema = TipoSistema.WEB if framework != "express" else TipoSistema.FULLSTACK
        perfil = "npm_script"
        entrypoint = entrypoints.get(framework) or entrypoints.get("express")
        script = "dev" if "dev" in scripts_npm else "start" if "start" in scripts_npm else None
        comando = ["npm", "run", script] if script else []
    elif framework == "html_estatico":
        tipo_sistema = TipoSistema.WEB
        perfil = "http_server"
        entrypoint = None
        comando = ["python", "-m", "http.server", "8000"]
    else:
        tipo_sistema = TipoSistema.DESCONHECIDO
        perfil = None
        entrypoint = None
        comando = []

    rotas_unicas: list[RotaDescobertaE2E] = []
    chaves_rotas: set[tuple[str, str | None]] = set()
    for rota in rotas:
        chave = (rota.rota, rota.metodo)
        if chave not in chaves_rotas:
            chaves_rotas.add(chave)
            rotas_unicas.append(rota)
    confianca = 0.95 if maior_pontuacao >= 5 else 0.8 if maior_pontuacao >= 3 else 0.65 if maior_pontuacao >= 2 else 0.2
    return ProjetoInspecionadoE2E(
        framework=framework,
        tipo_sistema=tipo_sistema,
        linguagens=list(dict.fromkeys(linguagens)),
        entrypoint=entrypoint,
        perfil_inicializacao=perfil,
        comando_inicializacao_sugerido=comando,
        rotas=rotas_unicas,
        contratos_api=contratos_api,
        arquivos_analisados=[arquivo.nome for arquivo in arquivos],
        sinais_encontrados=list(dict.fromkeys(sinais)),
        confianca=confianca,
        limites_atingidos=list(dict.fromkeys(limites)),
        bloqueios=bloqueios,
    )


def inspecionar_projeto_e2e(
    entrada: EntradaE2ENormalizada,
    workspace_projeto: str | None = None,
) -> ProjetoInspecionadoE2E:
    """Descobre framework, entrypoint e rotas sem executar código do projeto."""

    arquivos = [
        _ArquivoInspecao(item.nome, item.conteudo) for item in entrada.codigo_fonte
    ]
    arquivos_workspace, limites, bloqueios = _arquivos_do_workspace(workspace_projeto)
    nomes_inline = {arquivo.nome for arquivo in arquivos}
    arquivos.extend(
        arquivo for arquivo in arquivos_workspace if arquivo.nome not in nomes_inline
    )
    if not arquivos and not bloqueios:
        bloqueios.append(
            "Nenhum código_fonte ou workspace_projeto foi fornecido para inspeção."
        )
    return _inspecionar_arquivos(arquivos, limites, bloqueios)
