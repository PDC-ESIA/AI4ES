"""Execução do QA em contêiner descartável; nunca faz fallback para o host."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from shared.qa_disclosure import arquivo_privado, TIPOS_ERRO


class SandboxIndisponivel(RuntimeError):
    pass


_EXTENSOES = {".py", ".ts", ".js", ".json", ".html", ".css", ".txt", ".csv"}
_IGNORADOS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
              "prompts", "secrets", "credentials", "doubt_artifacts"}
_PRIVADOS = {"prompt.py", "prompts.py", "credentials.json", "secrets.json",
             "package.json", "package-lock.json", "report.json", "coverage.json"}


def copiar_entrada(origem: Path, destino: Path) -> None:
    """Snapshot limitado: sem links, credenciais/configuração ou arquivos especiais."""
    origem = origem.resolve(strict=True)
    total = 0
    quantidade = 0
    for pasta, dirs, arquivos in os.walk(origem, followlinks=False):
        base = Path(pasta)
        for nome in [*dirs, *arquivos]:
            item = base / nome
            if item.is_symlink() or item.is_junction():
                raise ValueError("Links não são permitidos na entrada do QA.")
        dirs[:] = [nome for nome in dirs if nome not in _IGNORADOS and not nome.startswith(".")]
        for nome in arquivos:
            item = base / nome
            if (nome.startswith(".") or nome.lower() in _PRIVADOS or arquivo_privado(item.relative_to(origem))
                    or item.suffix.lower() not in _EXTENSOES):
                continue
            if not item.is_file() or not item.resolve().is_relative_to(origem):
                raise ValueError("Arquivo inválido na entrada do QA.")
            tamanho = item.stat().st_size
            total += tamanho
            quantidade += 1
            if tamanho > 2_000_000 or total > 20_000_000 or quantidade > 1000:
                raise ValueError("Entrada do QA excede o limite de tamanho.")
            alvo = destino / item.relative_to(origem)
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, alvo)
            alvo.chmod(0o644)


def executar_isolado(suite: Path, teste: str, *, modo: str = "pytest",
                     projeto: Path | None = None, entrypoint: str | None = None,
                     timeout: int = 30) -> dict:
    """Monta somente um snapshot RO; rede, privilégios e recursos restritos.

    Imagem previamente construída pelo operador. Não recebe opções Docker,
    dependências ou variáveis de ambiente do modelo.
    """
    if modo not in {"pytest", "playwright"} or Path(teste).name != teste:
        raise ValueError("Perfil ou nome de teste inválido.")
    if modo == "playwright" and (projeto is None or not entrypoint):
        raise ValueError("E2E exige aplicação gerenciada dentro do contêiner.")
    cliente = None
    container = None
    try:
        import docker
        cliente = docker.from_env(timeout=10)
        # get não baixa imagens e usar o ID evita troca da tag entre get/create.
        imagem = cliente.images.get(os.environ.get("QA_SANDBOX_IMAGE", "ai4es-qa-sandbox:local"))
        with tempfile.TemporaryDirectory(prefix="qa-input-") as temporario:
            snapshot = Path(temporario)
            snapshot.chmod(0o755)
            copiar_entrada(suite, snapshot / "suite")
            if projeto is not None:
                copiar_entrada(projeto, snapshot / "app")
            for pasta in snapshot.rglob("*"):
                if pasta.is_dir():
                    pasta.chmod(0o755)
            (snapshot / "job.json").write_text(json.dumps({
                "modo": modo, "teste": teste, "entrypoint": entrypoint,
                "timeout": max(5, min(timeout, 300)),
            }), encoding="utf-8")
            (snapshot / "job.json").chmod(0o644)
            container = cliente.containers.create(
                image=imagem.id,
                entrypoint=["python", "-I", "/opt/qa/run.py"], command=[],
                network_mode="none", read_only=True, user="1000:1000",
                cap_drop=["ALL"], security_opt=["no-new-privileges:true"],
                mem_limit="1g", nano_cpus=1_000_000_000, pids_limit=128,
                tmpfs={"/work": "rw,nosuid,nodev,size=128m,uid=1000,gid=1000",
                       "/tmp": "rw,nosuid,nodev,size=128m,uid=1000,gid=1000"},
                volumes={str(snapshot): {"bind": "/input", "mode": "ro"}},
                working_dir="/work", environment={"HOME": "/tmp", "PYTHONUTF8": "1"},
                log_config=docker.types.LogConfig(type="json-file", config={
                    "max-size": "1m", "max-file": "1"}),
            )
            try:
                container.start()
                container.wait(timeout=max(5, min(timeout, 300)) + 10)
                raw = container.logs(stdout=True, stderr=False, tail=1)
                if len(raw) > 100_000:
                    raise ValueError("Resultado do QA excedeu o limite.")
                resultado = json.loads(raw)
                if not isinstance(resultado, dict):
                    raise ValueError("Resultado do QA inválido.")
                # Nenhum texto livre do processo atravessa esta fronteira.
                seguro = {chave: _contador(resultado.get(chave)) for chave in (
                    "passed", "failed", "skipped", "exit_code", "covered_lines", "num_statements"
                )}
                seguro["exit_code"] = 0 if type(resultado.get("exit_code")) is int and resultado["exit_code"] == 0 else 1
                erros = resultado.get("errors", [])
                seguro["errors"] = [
                    {"line": _contador(erro.get("line")),
                     "type": erro.get("type") if erro.get("type") in TIPOS_ERRO else "TestFailure"}
                    for erro in erros[:20] if isinstance(erro, dict) and isinstance(erro.get("type"), str)
                ] if isinstance(erros, list) else []
                return seguro
            finally:
                # Remover antes de apagar o snapshot, inclusive em timeout.
                container.remove(force=True, v=True)
                container = None
    except (ValueError, OSError):
        raise
    except Exception:
        # Exceções do Docker podem incluir paths/URLs/credenciais do daemon.
        raise SandboxIndisponivel("Sandbox do QA indisponível; execução no host bloqueada.") from None
    finally:
        if container is not None:
            container.remove(force=True, v=True)
        if cliente is not None:
            cliente.close()


def _contador(valor: object) -> int:
    if type(valor) is not int or not 0 <= valor <= 1_000_000:
        return 0
    return valor
