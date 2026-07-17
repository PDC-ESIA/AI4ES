"""Execução local e controlada de um spec Playwright recém-gerado."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from shared.workspace import get_agent_workspace

from ..schemas import EntradaE2ENormalizada, ResultadoExecucaoE2E

_PERFIS_COMANDO_PERMITIDOS = {
    "playwright test",
    "npx playwright test",
    "pnpm exec playwright test",
    "npm run e2e:test",
}
_TIMEOUT_MINIMO_SEGUNDOS = 5
_TIMEOUT_MAXIMO_SEGUNDOS = 300


def _project_root() -> Path:
    return Path(__file__).resolve().parents[6]


def _resolver_node() -> Path | None:
    configurado = os.environ.get("PLAYWRIGHT_NODE_EXECUTABLE", "").strip()
    if configurado:
        caminho = Path(configurado).expanduser().resolve()
        return caminho if caminho.is_file() else None

    encontrado = shutil.which("node")
    return Path(encontrado).resolve() if encontrado else None


def _valor_inteiro(
    ambiente: dict[str, Any],
    chave: str,
    padrao: int,
    minimo: int,
    maximo: int,
) -> int:
    try:
        valor = int(ambiente.get(chave, padrao))
    except TypeError, ValueError:
        return padrao
    return max(minimo, min(valor, maximo))


def _logs_resumidos(stdout: str, stderr: str) -> list[str]:
    linhas = [
        linha.strip() for linha in f"{stdout}\n{stderr}".splitlines() if linha.strip()
    ]
    return [linha[:500] for linha in linhas[-20:]]


def _coletar_falhas(relatorio: dict[str, Any]) -> list[dict[str, Any]]:
    falhas: list[dict[str, Any]] = []

    def visitar(no: dict[str, Any], caminho: list[str]) -> None:
        titulo_no = str(no.get("title") or "").strip()
        caminho_atual = [*caminho, titulo_no] if titulo_no else caminho
        for spec in no.get("specs", []):
            titulo_spec = str(spec.get("title") or "Teste Playwright")
            for teste in spec.get("tests", []):
                status = str(teste.get("status") or "desconhecido")
                if status in {"expected", "skipped"}:
                    continue
                mensagens: list[str] = []
                for resultado in teste.get("results", []):
                    for erro in resultado.get("errors", []):
                        mensagem = str(erro.get("message") or erro.get("value") or "")
                        if mensagem:
                            mensagens.append(mensagem[:2_000])
                falhas.append(
                    {
                        "teste": " > ".join([*caminho_atual, titulo_spec]),
                        "status": status,
                        "mensagens": mensagens[:5],
                    }
                )
                if len(falhas) >= 20:
                    return
        for suite in no.get("suites", []):
            if len(falhas) >= 20:
                return
            visitar(suite, caminho_atual)

    visitar(relatorio, [])
    return falhas


def _resultado_do_relatorio(
    relatorio: dict[str, Any],
    *,
    comando: str,
    codigo_saida: int,
    duracao_ms: int,
    arquivo_relatorio: Path,
    diretorio_artefatos: Path,
    stdout: str,
    stderr: str,
) -> ResultadoExecucaoE2E:
    stats = relatorio.get("stats", {})
    aprovados = int(stats.get("expected", 0) or 0)
    falhos = int(stats.get("unexpected", 0) or 0)
    instaveis = int(stats.get("flaky", 0) or 0)
    pulados = int(stats.get("skipped", 0) or 0)
    falhos += instaveis
    executados = aprovados + falhos + pulados
    status = "aprovado" if codigo_saida == 0 and falhos == 0 else "falhou"
    return ResultadoExecucaoE2E(
        status=status,
        comando=comando,
        codigo_saida=codigo_saida,
        duracao_ms=duracao_ms,
        testes_executados=executados,
        testes_aprovados=aprovados,
        testes_falhos=falhos,
        testes_pulados=pulados,
        arquivo_relatorio=str(arquivo_relatorio),
        diretorio_artefatos=str(diretorio_artefatos),
        falhas=_coletar_falhas(relatorio),
        logs_resumidos=_logs_resumidos(stdout, stderr),
    )


def executar_playwright(
    entrada: EntradaE2ENormalizada,
    arquivo_spec: str,
) -> ResultadoExecucaoE2E:
    """Executa um spec com argv fixo, sem shell e com timeout limitado."""

    perfil = (entrada.comando_execucao or "").strip().lower()
    if perfil not in _PERFIS_COMANDO_PERMITIDOS:
        return ResultadoExecucaoE2E(
            status="bloqueado_infraestrutura",
            logs_resumidos=["Perfil de comando Playwright não permitido."],
        )

    destino = get_agent_workspace("e2e_test_generator").resolve()
    arquivo = Path(arquivo_spec).resolve()
    if destino not in arquivo.parents or not arquivo.is_file():
        return ResultadoExecucaoE2E(
            status="bloqueado_infraestrutura",
            logs_resumidos=["Spec ausente ou fora do workspace reservado do E2E."],
        )

    raiz = _project_root()
    config = raiz / "playwright.config.ts"
    cli = raiz / "node_modules" / "@playwright" / "test" / "cli.js"
    node = _resolver_node()
    ausentes = [
        nome
        for nome, existe in {
            "Node.js": node is not None,
            "@playwright/test": cli.is_file(),
            "playwright.config.ts": config.is_file(),
        }.items()
        if not existe
    ]
    if ausentes:
        return ResultadoExecucaoE2E(
            status="bloqueado_infraestrutura",
            logs_resumidos=[
                "Runtime ausente: " + ", ".join(ausentes) + ".",
                "Execute npm install e npx playwright install chromium.",
            ],
        )

    ambiente = entrada.ambiente_execucao
    timeout_segundos = _valor_inteiro(
        ambiente,
        "timeout_segundos",
        120,
        _TIMEOUT_MINIMO_SEGUNDOS,
        _TIMEOUT_MAXIMO_SEGUNDOS,
    )
    timeout_teste_ms = _valor_inteiro(
        ambiente,
        "timeout_teste_ms",
        30_000,
        1_000,
        120_000,
    )
    relatorio = destino / f"{arquivo.stem}.playwright-report.json"
    artefatos = destino / "test-results" / arquivo.stem
    if relatorio.exists():
        relatorio.unlink()

    env = os.environ.copy()
    env.update(
        {
            "E2E_TEST_DIR": str(destino),
            "E2E_SPEC_NAME": arquivo.name,
            "E2E_ARTIFACTS_DIR": str(artefatos),
            "E2E_TEST_TIMEOUT_MS": str(timeout_teste_ms),
            "E2E_GLOBAL_TIMEOUT_MS": str(timeout_segundos * 1_000),
            "PLAYWRIGHT_JSON_OUTPUT_FILE": str(relatorio),
        }
    )
    argv = [str(node), str(cli), "test", "--config", str(config)]
    comando_exibido = "node @playwright/test/cli.js test --config playwright.config.ts"
    inicio = time.monotonic()
    try:
        processo = subprocess.run(
            argv,
            cwd=raiz,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_segundos,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        duracao_ms = int((time.monotonic() - inicio) * 1_000)
        return ResultadoExecucaoE2E(
            status="timeout",
            comando=comando_exibido,
            duracao_ms=duracao_ms,
            diretorio_artefatos=str(artefatos),
            logs_resumidos=_logs_resumidos(
                str(exc.stdout or ""),
                str(exc.stderr or ""),
            ),
        )
    except OSError as exc:
        return ResultadoExecucaoE2E(
            status="erro_execucao",
            comando=comando_exibido,
            logs_resumidos=[f"Falha ao iniciar Playwright: {exc}"],
        )

    duracao_ms = int((time.monotonic() - inicio) * 1_000)
    if not relatorio.is_file():
        return ResultadoExecucaoE2E(
            status="erro_execucao",
            comando=comando_exibido,
            codigo_saida=processo.returncode,
            duracao_ms=duracao_ms,
            diretorio_artefatos=str(artefatos),
            logs_resumidos=_logs_resumidos(processo.stdout, processo.stderr),
        )
    try:
        conteudo_relatorio = json.loads(relatorio.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ResultadoExecucaoE2E(
            status="erro_execucao",
            comando=comando_exibido,
            codigo_saida=processo.returncode,
            duracao_ms=duracao_ms,
            arquivo_relatorio=str(relatorio),
            diretorio_artefatos=str(artefatos),
            logs_resumidos=[
                f"Relatório Playwright inválido: {exc}",
                *_logs_resumidos(processo.stdout, processo.stderr),
            ],
        )
    return _resultado_do_relatorio(
        conteudo_relatorio,
        comando=comando_exibido,
        codigo_saida=processo.returncode,
        duracao_ms=duracao_ms,
        arquivo_relatorio=relatorio,
        diretorio_artefatos=artefatos,
        stdout=processo.stdout,
        stderr=processo.stderr,
    )
