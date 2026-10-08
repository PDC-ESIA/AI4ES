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

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from shared.execution.manifest import ManifestError, load_manifest
from shared.execution.sandbox import create_sandbox
from shared.execution.trilhas import ambiente_da_trilha
from shared.tools.coding_tools.aceite_independente import comando_de_aceite

logger = logging.getLogger(__name__)

PASTA_JORNADA = "tests/journey"
ARQUIVO_JORNADA = f"{PASTA_JORNADA}/test_jornada.py"
ARQUIVO_CONFTEST = f"{PASTA_JORNADA}/conftest.py"

# conftest da jornada de produtos web (Playwright). Gravado pelo pipeline na
# pasta protegida: o coder não o edita, e ele vale para todo teste da jornada.
#   - `base_url` vem de AI4ES_JORNADA_URL (o produto subido pelo run.json), e
#     `page.goto("/")` resolve contra ela;
#   - toda resposta do PRÓPRIO produto com 4xx/5xx e todo erro de JavaScript
#     na página reprovam a jornada — imagem quebrada, CSS ausente, fragmento
#     htmx com 500. Status esperados num teste: @pytest.mark.permite_status(422).
CONFTEST_JORNADA = '''"""Gerado pelo pipeline (protegido): fixtures da jornada de produtos web."""
import os
from urllib.parse import urlparse

import pytest


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
def _recursos_do_produto(request, base_url):
    if "page" not in request.fixturenames:
        yield
        return
    page = request.getfixturevalue("page")
    host = urlparse(base_url).netloc
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


def usa_navegador(codigo: str) -> bool:
    """A jornada usa o Playwright (produto web navegado pela interface)?"""
    return "playwright" in codigo


def instalar_conftest(workdir: Path) -> None:
    destino = workdir / ARQUIVO_CONFTEST
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(CONFTEST_JORNADA, encoding="utf-8")

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


def executar_jornada(coder_dir: Path, trilha: Optional[dict] = None) -> ResultadoJornada:
    """Constrói o artefato, sobe o serviço COMO O `run.json` MANDA e percorre a jornada.

    Sem variáveis de ambiente extras de propósito: os testes de aceite isolam
    banco e pastas, e na validação isso escondeu um app que, na configuração
    padrão, gravava uploads em `/storage` (raiz do sistema) e quebrava com 500.
    A jornada é o único teste que usa o produto como o usuário o recebe.
    """
    from shared.tools.coding_tools.harness_execucao import _testes_da_saida

    try:
        manifest = load_manifest(coder_dir / "run.json")
    except ManifestError as exc:
        return ResultadoJornada(NAO_EXECUTADA, motivo=f"run.json inválido: {exc}")
    workdir = (coder_dir / manifest.workdir).resolve()
    if not (workdir / ARQUIVO_JORNADA).is_file():
        return ResultadoJornada(NAO_EXECUTADA, motivo="teste de jornada não foi escrito")
    comando = comando_de_aceite(manifest.test, ARQUIVO_JORNADA)
    if comando is None:
        return ResultadoJornada(NAO_EXECUTADA, motivo="o run.json não usa pytest")

    navegador = usa_navegador(
        (workdir / ARQUIVO_JORNADA).read_text(encoding="utf-8", errors="replace")
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
                instalar_conftest(Path(sandbox.workdir))
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
