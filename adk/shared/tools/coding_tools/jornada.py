"""Teste de jornada do produto integrado (`AI4ES_JORNADA`).

Cada task do coder é validada isoladamente; ninguém testava o produto inteiro.
Na run do fotógrafo as 7 tasks passaram e o fluxo real quebrava nas costuras:
imagens com 404 (caminho relativo, sem rota servindo o storage), formulário de
álbum enviado a um endpoint que só aceitava JSON (422), nenhuma tela de upload.

Depois da última task, um agente escreve `tests/journey/test_jornada.py` a
partir das HUs — os fluxos de ponta a ponta, com checagem dos recursos que as
páginas referenciam — e este módulo o executa no mesmo ambiente do harness
(build do `run.json`, trilha). Falhou, vira uma task de integração.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from shared.execution.manifest import ManifestError, load_manifest
from shared.execution.sandbox import create_sandbox
from shared.execution.trilhas import ambiente_da_trilha
from shared.tools.coding_tools.aceite_independente import (
    comando_de_aceite,
    e_arquivo_de_interface,
)

logger = logging.getLogger(__name__)

PASTA_JORNADA = "tests/journey"
ARQUIVO_JORNADA = f"{PASTA_JORNADA}/test_jornada.py"
ARQUIVO_CONFTEST = f"{PASTA_JORNADA}/conftest.py"

# conftest dos testes de produto web pelo navegador (Playwright): a jornada e
# os critérios de interface. Gravado pelo pipeline nas pastas protegidas: o
# coder não o edita. Testes sem `page` (TestClient) não são afetados.
#   - `base_url` vem de AI4ES_JORNADA_URL (o produto subido pelo run.json), e
#     `page.goto("/")` resolve contra ela;
#   - toda resposta do PRÓPRIO produto com 4xx/5xx e todo erro de JavaScript
#     na página reprovam a jornada — imagem quebrada, CSS ausente, fragmento
#     htmx com 500. Status esperados num teste: @pytest.mark.permite_status(422).
CONFTEST_JORNADA = '''"""Gerado pelo pipeline (protegido): fixtures da jornada de produtos web."""
import os
import struct
import uuid
import zlib
from urllib.parse import urlparse

import pytest


# ── Helpers determinísticos (use-os em vez de reescrever) ────────────────


@pytest.fixture
def nome_unico():
    """`nome_unico("Ensaio")` -> "Ensaio 1a2b3c4d": dado único por teste (o
    servidor é compartilhado entre testes e tasks)."""

    def _gerar(prefixo="teste"):
        return f"{prefixo} {uuid.uuid4().hex[:8]}"

    return _gerar


def _png(largura, altura, cor):
    linha = b"\\x00" + bytes(cor) * largura
    bruto = zlib.compress(linha * altura)

    def bloco(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(
            ">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF
        )

    cabecalho = struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0)
    return b"\\x89PNG\\r\\n\\x1a\\n" + bloco(b"IHDR", cabecalho) + bloco(b"IDAT", bruto) + bloco(b"IEND", b"")


@pytest.fixture
def imagens(tmp_path):
    """`imagens(3, "jpeg", (1200, 800))` -> lista de caminhos de imagens válidas
    e distintas, prontas para `set_input_files` ou para upload no TestClient.
    JPEG exige Pillow; PNG funciona sem dependência nenhuma."""

    def _gerar(n=1, formato="jpeg", tamanho=(64, 48)):
        formato = formato.lower().replace("jpg", "jpeg")
        caminhos = []
        for i in range(n):
            cor = ((40 * i) % 256, (90 + 30 * i) % 256, (160 + 50 * i) % 256)
            destino = tmp_path / f"foto_{i + 1:03d}.{'jpg' if formato == 'jpeg' else formato}"
            if formato == "png":
                destino.write_bytes(_png(tamanho[0], tamanho[1], cor))
            else:
                from PIL import Image

                Image.new("RGB", tamanho, cor).save(destino, formato.upper())
            caminhos.append(destino)
        return caminhos

    return _gerar


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "permite_status(*codigos): status HTTP do produto esperados neste teste"
    )


@pytest.fixture(scope="session")
def base_url():
    url = os.environ.get("AI4ES_JORNADA_URL")
    if not url:
        pytest.skip("AI4ES_JORNADA_URL ausente: a jornada roda contra o produto no ar.")
    return url


@pytest.fixture(autouse=True)
def _recursos_do_produto(request):
    if "page" not in request.fixturenames:
        yield
        return
    page = request.getfixturevalue("page")
    host = urlparse(request.getfixturevalue("base_url")).netloc
    marcador = request.node.get_closest_marker("permite_status")
    permitidos = set(marcador.args) if marcador else set()
    falhas = []

    def _resposta(resposta):
        if urlparse(resposta.url).netloc == host and resposta.status >= 400:
            if resposta.status not in permitidos:
                falhas.append(
                    f"{resposta.request.method} {urlparse(resposta.url).path} -> {resposta.status}"
                )

    def _erro_js(erro):
        falhas.append(f"erro de JavaScript na página: {erro}")

    page.on("response", _resposta)
    page.on("pageerror", _erro_js)
    yield
    if falhas:
        pytest.fail(
            "O produto respondeu com erro durante a jornada:\\n" + "\\n".join(falhas),
            pytrace=False,
        )
'''


def limites_do_navegador() -> dict:
    """Limites do sandbox para rodar o Chromium.

    O DirectSandbox limita o espaço de endereçamento VIRTUAL a 2 GiB, pensado
    para os comandos do coder; um navegador reserva bem mais que isso só para
    subir e aborta na inicialização ("Target page, context or browser has been
    closed"). Wall-clock e CPU continuam limitados.
    """
    try:
        import resource

        sem_limite = resource.RLIM_INFINITY
    except ImportError:  # pragma: no cover — sem `resource`, não há limite a afrouxar
        return {}
    return {"mem_bytes": sem_limite, "cpu_seconds": 600}


def usa_navegador(codigo: str, arquivo_rel: str = "") -> bool:
    """O arquivo navega pelo produto (Playwright)?

    Os testes de interface do aceite são sempre de navegador, mesmo sem citar
    o Playwright (usam só a fixture `page`).
    """
    return "playwright" in codigo or (bool(arquivo_rel) and e_arquivo_de_interface(arquivo_rel))


def instalar_conftest(workdir: Path, pasta: str = PASTA_JORNADA) -> None:
    destino = workdir / pasta / "conftest.py"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(CONFTEST_JORNADA, encoding="utf-8")


# No modo navegador, nada de atalhos que pulam a interface.
_MODULOS_PROIBIDOS = ("httpx", "requests", "urllib", "aiohttp", "fastapi", "starlette", "flask", "app")

# Métodos do Playwright que executam ou injetam código na página, ou desviam
# requisições. Na oitava validação o autor, impedido de usar httpx, injetou um
# <input type=file> que a interface não tinha (`page.evaluate`) e fez o upload
# por `fetch` — o mesmo atalho, por dentro do navegador. O usuário não roda
# JavaScript no console para usar o produto.
_METODOS_PROIBIDOS = frozenset(
    {
        "evaluate",
        "evaluate_handle",
        "eval_on_selector",
        "eval_on_selector_all",
        "evaluate_all",
        "add_script_tag",
        "add_init_script",
        "wait_for_function",
        "set_content",
        "route",
        "route_from_har",
        "expose_function",
        "expose_binding",
        "dispatch_event",
    }
)


# Seletor CSS por classe (`.btn-upload`, `button.btn-upload`): depende de um
# detalhe que só o código atual conhece.
_SELETOR_DE_CLASSE = re.compile(r"(^|[\s>+~,(])[\w-]*\.[A-Za-z_][\w-]*")
_ASSERCOES = re.compile(r"^(to_|not_to_)")


def violacoes_de_robustez(arvore: ast.AST) -> list[str]:
    """Padrões que tornam um teste de interface frágil ou inválido.

    Na 11ª validação os testes de interface do aceite traziam `to_have_count(
    lambda c: ...)` (o Playwright recusa função: o teste quebra depois de a
    tela funcionar), cascatas "tenta o data-testid, senão `.first`, senão
    `button.btn-upload`" dentro de `try/except`, e escolha de item por
    posição. Cada um custou uma task travada sem defeito no produto.
    """
    erros: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Try):
            erros.append(
                "`try/except` no teste: não tente alternativas nem engula falhas; "
                "localize por `data-testid` e deixe o teste falhar."
            )
        if isinstance(no, ast.Attribute) and no.attr in ("first", "last"):
            erros.append(
                f"`.{no.attr}`: não escolha elemento por posição; localize pelo "
                "`data-testid` e, em listas, pelo conteúdo (`filter(has_text=...)`)."
            )
        if not (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)):
            continue
        metodo = no.func.attr
        if metodo == "nth":
            erros.append("`.nth(...)`: não escolha elemento por posição.")
        if _ASSERCOES.match(metodo) and any(
            isinstance(a, ast.Lambda) for a in [*no.args, *(k.value for k in no.keywords)]
        ):
            erros.append(
                f"`.{metodo}(lambda ...)`: as asserções do Playwright aceitam texto, "
                "número ou regex — nunca função."
            )
        if metodo == "locator" and no.args:
            alvo = no.args[0]
            if isinstance(alvo, ast.Constant) and isinstance(alvo.value, str) and _SELETOR_DE_CLASSE.search(alvo.value):
                erros.append(
                    f"`locator({alvo.value!r})`: seletor por classe CSS; use `get_by_test_id`."
                )
    for no in ast.walk(arvore):
        if isinstance(no, ast.If) and any(
            isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in ("count", "is_visible")
            for c in ast.walk(no.test)
        ):
            erros.append(
                "`if ...count()/is_visible()`: não ramifique pela existência de "
                "elementos; o teste especifica UMA interface."
            )
    return sorted(set(erros))


def identificadores_existentes(workdir: Path, limite: int = 200) -> list[str]:
    """`data-testid` já usados nas telas e nos testes de interface anteriores."""
    encontrados: set[str] = set()
    padroes = (
        re.compile(r"""data-testid\s*=\s*["']([^"'{}<>]+)["']"""),
        re.compile(r"""get_by_test_id\(\s*["']([^"']+)["']"""),
    )
    for caminho in sorted(workdir.rglob("*")):
        if not caminho.is_file() or caminho.suffix not in (".html", ".jinja", ".jinja2", ".j2", ".py", ".js"):
            continue
        if any(p in ("venv", ".venv", "node_modules", "__pycache__") for p in caminho.parts):
            continue
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for padrao in padroes:
            encontrados.update(padrao.findall(texto))
        if len(encontrados) >= limite:
            break
    return sorted(encontrados)[:limite]


# Falha que vem do PRÓPRIO teste (não do produto): o coder não pode consertar —
# o teste é protegido —, então ele volta ao autor.
_ERRO_DO_TESTE = re.compile(
    r"\b(TypeError|NameError|AttributeError|ImportError|ModuleNotFoundError|SyntaxError|"
    r"UnboundLocalError|IndentationError)\b|fixture '[^']+' not found|"
    r"_errors\.Error: (?!.*Timeout)(value must|Unsupported|expected)",
)


def erro_do_proprio_teste(saida: str) -> bool:
    return bool(_ERRO_DO_TESTE.search(saida or ""))


def violacoes_do_modo_navegador(arvore: ast.AST) -> list[str]:
    """O que, num teste de produto web pelo navegador (jornada ou critério de
    interface), pula a interface do produto.

    Na sétima validação a jornada chamou os endpoints direto e passou, com um
    produto sem tela de upload, sem botão de seleção e sem tela de álbum.
    """
    erros: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes = [a.name for a in no.names]
        elif isinstance(no, ast.ImportFrom):
            nomes = [no.module or ""]
        else:
            nomes = []
        for nome in nomes:
            if nome.split(".")[0] in _MODULOS_PROIBIDOS:
                erros.append(f"import de `{nome}`: teste de produto web usa só o navegador (`page`).")
        if isinstance(no, ast.Attribute) and no.attr == "request" and isinstance(no.value, ast.Name):
            erros.append(
                f"`{no.value.id}.request` faz HTTP direto, sem passar pela interface."
            )
        if (
            isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and no.func.attr in _METODOS_PROIBIDOS
        ):
            erros.append(
                f"`.{no.func.attr}(...)` executa ou injeta código na página; o teste "
                "só clica, preenche e lê o que a interface mostra."
            )
        if (
            isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and no.func.attr == "goto"
        ):
            alvo = no.args[0] if no.args else None
            if not (isinstance(alvo, ast.Constant) and alvo.value == "/"):
                erros.append(
                    "`page.goto(...)` só pode abrir a página inicial `\"/\"`; o resto se "
                    "alcança clicando em links e botões, como o usuário faria."
                )
    usa_page = any(
        isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
        and no.name.startswith("test_")
        and any(a.arg == "page" for a in no.args.args)
        for no in ast.walk(arvore)
    )
    if not usa_page:
        erros.append("Nenhum teste recebe a fixture `page` do Playwright.")
    return sorted(set(erros))

_TIMEOUT_BUILD = 300
_TIMEOUT_JORNADA = 180

PASSOU = "passou"
FALHOU = "falhou"
NAO_EXECUTADA = "nao_executada"


@dataclass
class ResultadoJornada:
    status: str
    motivo: str = ""
    testes: list[dict] = field(default_factory=list)
    falhas: list[str] = field(default_factory=list)
    saida: str = ""

    def como_dict(self) -> dict:
        return asdict(self)


def _cauda(texto: str, limite: int = 6000) -> str:
    texto = (texto or "").strip()
    return texto if len(texto) <= limite else "…" + texto[-limite:]


# Variável com a URL do servidor real que o teste de jornada percorre.
VAR_URL = "AI4ES_JORNADA_URL"
_TIMEOUT_SUBIDA = 30


def preparar_cliente_http(
    sandbox, comando_pytest: str, env: Optional[dict], *, navegador: bool = False
) -> None:
    """Garante as dependências da jornada no ambiente do pytest (best-effort).

    O projeto não precisa declará-las: `httpx` (modo HTTP) e, para produtos
    web, `pytest-playwright` + Chromium (o navegador fica no cache do usuário,
    `~/.cache/ms-playwright`, e só é baixado na primeira vez). Usa o pip do
    mesmo interpretador do comando pytest (`venv/bin/python -m pytest` →
    `venv/bin/python -m pip`), com as restrições da trilha.
    """
    prefixo = comando_pytest.split(" -m pytest")[0] if " -m pytest" in comando_pytest else ""
    if not prefixo:
        return
    pacotes = "httpx pytest-playwright" if navegador else "httpx"
    sandbox.exec(f"{prefixo} -m pip install -q {pacotes}", timeout=_TIMEOUT_BUILD, env=env)
    if navegador:
        sandbox.exec(f"{prefixo} -m playwright install chromium", timeout=600, env=env)


def esperar_servico(url: str, timeout: float = _TIMEOUT_SUBIDA) -> Optional[str]:
    """None quando o servidor responde (< 500); senão o último erro."""
    import time
    import urllib.error
    import urllib.request

    fim = time.time() + timeout
    erro = "sem resposta"
    while time.time() < fim:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status < 500:
                    return None
                erro = f"HTTP {resp.status}"
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                return None
            erro = f"HTTP {exc.code}"
        except OSError as exc:
            erro = str(exc)
        time.sleep(1)
    return erro


def executar_jornada(
    coder_dir: Path, trilha: Optional[dict] = None, arquivo: str = ARQUIVO_JORNADA
) -> ResultadoJornada:
    """Constrói o artefato, sobe o serviço COMO O `run.json` MANDA e percorre a jornada.

    Sem variáveis de ambiente extras de propósito: os testes de aceite isolam
    banco e pastas, e na validação isso escondeu um app que, na configuração
    padrão, gravava uploads em `/storage` (raiz do sistema) e quebrava com 500.
    A jornada é o único teste que usa o produto como o usuário o recebe.

    `arquivo` permite rodar do mesmo jeito os critérios de interface de uma
    task (produto web), que também percorrem o produto no ar.
    """
    from shared.tools.coding_tools.harness_execucao import _testes_da_saida

    try:
        manifest = load_manifest(coder_dir / "run.json")
    except ManifestError as exc:
        return ResultadoJornada(NAO_EXECUTADA, motivo=f"run.json inválido: {exc}")
    workdir = (coder_dir / manifest.workdir).resolve()
    if not (workdir / arquivo).is_file():
        return ResultadoJornada(NAO_EXECUTADA, motivo=f"{arquivo} não foi escrito")
    comando = comando_de_aceite(manifest.test, arquivo)
    if comando is None:
        return ResultadoJornada(NAO_EXECUTADA, motivo="o run.json não usa pytest")

    navegador = usa_navegador(
        (workdir / arquivo).read_text(encoding="utf-8", errors="replace"), arquivo
    )
    sandbox = create_sandbox(
        "direct",
        workdir_subpath=manifest.workdir,
        **(limites_do_navegador() if navegador else {}),
    )
    try:
        sandbox.setup(coder_dir)
        env = {**ambiente_da_trilha(trilha, sandbox.root), **(manifest.env or {})}
        for build in manifest.build:
            res = sandbox.exec(build, timeout=_TIMEOUT_BUILD, env=env or None)
            if res.timed_out or res.exit_code != 0:
                saida = "\n".join(p for p in (res.stdout, res.stderr) if p)
                return ResultadoJornada(
                    FALHOU, motivo=f"build falhou: {build}", saida=_cauda(saida)
                )
        env_teste = dict(env)
        if manifest.surface == "service" and manifest.run and manifest.port:
            url = f"http://localhost:{manifest.port}"
            sandbox.start_service(manifest.run, env=env or None)
            erro = esperar_servico(url + (manifest.healthcheck or "/"))
            if erro is not None:
                return ResultadoJornada(
                    FALHOU,
                    motivo=f"a aplicação não subiu com o run.json ({erro})",
                    saida=_cauda(sandbox.logs()),
                )
            env_teste[VAR_URL] = url
            if navegador:
                # Conftest sempre fresco na cópia: é ele que reprova recurso quebrado.
                instalar_conftest(Path(sandbox.workdir), str(Path(arquivo).parent))
            preparar_cliente_http(sandbox, comando, env or None, navegador=navegador)
        res = sandbox.exec(comando, timeout=_TIMEOUT_JORNADA, env=env_teste or None)
        logs_servico = sandbox.logs()
    finally:
        sandbox.cleanup()

    saida = "\n".join(p for p in (res.stdout, res.stderr) if p)
    testes = _testes_da_saida(saida)
    falhas = [t["nodeid"] for t in testes if t["outcome"] in ("falhou", "erro")]
    if falhas and logs_servico:
        # O traceback do servidor (ex.: 500 no upload) é o que explica a falha.
        saida = f"{saida}\n\n--- log do servidor (final) ---\n{logs_servico[-2500:]}"
    if res.timed_out:
        return ResultadoJornada(FALHOU, motivo="tempo limite", testes=testes, falhas=falhas, saida=_cauda(saida))
    if res.exit_code == 0 and testes and not falhas:
        return ResultadoJornada(PASSOU, testes=testes, saida=_cauda(saida, 1500))
    motivo = "testes da jornada falharam" if testes else "nenhum teste da jornada executou"
    return ResultadoJornada(FALHOU, motivo=motivo, testes=testes, falhas=falhas, saida=_cauda(saida))


def montar_task_integracao(resultado: ResultadoJornada, task_id: str, rodada: int) -> dict:
    """Task sintética que devolve ao coder as falhas da jornada.

    O único critério é a própria jornada passar; o mapa dela aponta para os
    testes da jornada, e o mecanismo de aceite independente o decide.
    """
    falhas = "\n".join(f"- {f}" for f in resultado.falhas) or f"- {resultado.motivo}"
    return {
        "id": task_id,
        "type": "integration",
        "complexity": "medium",
        "description": (
            f"Integração do produto (rodada {rodada}): a jornada de ponta a ponta "
            f"`{ARQUIVO_JORNADA}`, escrita a partir das HUs, falhou. Corrija o "
            "CÓDIGO para que os fluxos funcionem juntos — rotas, formulários, "
            "templates, arquivos estáticos e mídia servidos. Não edite o teste.\n\n"
            f"Falhas:\n{falhas}\n\nSaída (final):\n{resultado.saida[-2500:]}"
        ),
        "business_rules": [],
        "acceptance_criteria": [
            {
                "id": "CA-01",
                "description": f"A jornada de ponta a ponta `{ARQUIVO_JORNADA}` passa por inteiro.",
                "automatable": True,
            }
        ],
        "contract": {"inputs": [ARQUIVO_JORNADA], "outputs": [], "interfaces": []},
        "requirement_id": "",
        "requirement_refs": [],
        "design_refs": [],
    }
