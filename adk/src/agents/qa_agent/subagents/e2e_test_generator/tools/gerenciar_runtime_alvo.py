"""Inicialização controlada do sistema alvo para execução E2E local."""

import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from shared.workspace import get_agent_workspace, get_workspace_root

from ..schemas import EntradaE2ENormalizada, ProjetoInspecionadoE2E

_RAIZ_ADK = Path(__file__).resolve().parents[6]
_TIMEOUT_INICIALIZACAO_SEGUNDOS = 15
_ENTRYPOINT_UVICORN = re.compile(
    r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$"
)


@dataclass
class RuntimeAlvoE2E:
    status: str
    base_url: str | None = None
    iniciado_pelo_agente: bool = False
    workspace: str | None = None
    comando: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    tentativas: int = 0
    encerrado: bool = False
    _processo: subprocess.Popen[str] | None = field(
        default=None,
        repr=False,
    )

    def encerrar(self) -> None:
        if self._processo is None:
            return
        if self._processo.poll() is None:
            self._processo.terminate()
            try:
                self._processo.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._processo.kill()
                self._processo.wait(timeout=5)
        self.encerrado = True

    def como_dict(self) -> dict:
        return {
            "status": self.status,
            "base_url": self.base_url,
            "iniciado_pelo_agente": self.iniciado_pelo_agente,
            "workspace": self.workspace,
            "comando": self.comando,
            "logs": self.logs,
            "tentativas": self.tentativas,
            "encerrado": self.encerrado,
        }


def _esta_contido(caminho: Path, raiz: Path) -> bool:
    try:
        caminho.relative_to(raiz)
        return True
    except ValueError:
        return False


def _porta_loopback_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind(("127.0.0.1", 0))
        return int(servidor.getsockname()[1])


def _materializar_codigo_inline(
    entrada: EntradaE2ENormalizada,
) -> tuple[Path | None, list[str]]:
    assinatura = hashlib.sha256()
    for arquivo in entrada.codigo_fonte:
        assinatura.update(arquivo.nome.encode("utf-8", errors="replace"))
        assinatura.update(b"\0")
        assinatura.update(arquivo.conteudo.encode("utf-8", errors="replace"))
        assinatura.update(b"\0")
    try:
        raiz = (
            get_agent_workspace("e2e_test_generator")
            / "_runtime_target"
            / assinatura.hexdigest()[:16]
        ).resolve()
        raiz.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return None, [f"Não foi possível criar o runtime isolado: {exc}"]
    erros: list[str] = []
    for arquivo in entrada.codigo_fonte:
        relativo = PurePosixPath(arquivo.nome.replace("\\", "/"))
        if relativo.is_absolute() or ".." in relativo.parts:
            erros.append(f"Caminho de código inline bloqueado: {arquivo.nome}")
            continue
        destino = (raiz / Path(*relativo.parts)).resolve()
        if not _esta_contido(destino, raiz):
            erros.append(f"Caminho de código inline fora do runtime: {arquivo.nome}")
            continue
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(arquivo.conteudo, encoding="utf-8")
            if destino.suffix.lower() == ".py":
                pacote = destino.parent
                while pacote != raiz and _esta_contido(pacote, raiz):
                    init = pacote / "__init__.py"
                    if not init.exists():
                        init.write_text("", encoding="utf-8")
                    pacote = pacote.parent
        except OSError as exc:
            erros.append(f"Falha ao materializar {arquivo.nome}: {exc}")
    if erros or not entrada.codigo_fonte:
        return None, erros or ["Código inline ausente para iniciar o runtime."]
    return raiz, []


def _resolver_workspace(
    workspace_projeto: str | None,
    entrada: EntradaE2ENormalizada,
) -> tuple[Path | None, list[str]]:
    if not workspace_projeto:
        return _materializar_codigo_inline(entrada)
    candidato = Path(workspace_projeto).expanduser()
    if not candidato.is_absolute():
        candidato = _RAIZ_ADK / candidato
    candidato = candidato.resolve()
    raizes = {_RAIZ_ADK.resolve(), get_workspace_root().resolve()}
    if not any(_esta_contido(candidato, raiz) for raiz in raizes):
        return None, ["workspace_projeto fora das raízes permitidas."]
    if not candidato.is_dir():
        return None, ["workspace_projeto não existe ou não é um diretório."]
    return candidato, []


def _ambiente_minimo_runtime(workspace: Path) -> dict[str, str]:
    """Evita expor credenciais do processo pai ao código sob teste."""

    permitidas = {
        "SYSTEMROOT",
        "WINDIR",
        "PATH",
        "PATHEXT",
        "TEMP",
        "TMP",
        "PYTHONIOENCODING",
        "PYTHONUTF8",
    }
    env = {
        chave: valor
        for chave in permitidas
        if (valor := os.environ.get(chave)) is not None
    }
    env["PYTHONPATH"] = str(workspace)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _runtime_responde(
    base_url: str,
    processo: subprocess.Popen[str],
    rotas_esperadas: set[str],
) -> bool:
    url = base_url.rstrip("/") + "/openapi.json"
    limite = time.monotonic() + _TIMEOUT_INICIALIZACAO_SEGUNDOS
    while time.monotonic() < limite:
        if processo.poll() is not None:
            return False
        try:
            with urlopen(url, timeout=1) as resposta:
                if 200 <= resposta.status < 500:
                    try:
                        contrato = json.loads(resposta.read())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        contrato = {}
                    rotas_runtime = set(contrato.get("paths", {}))
                    if not rotas_esperadas or rotas_esperadas.intersection(
                        rotas_runtime
                    ):
                        return True
        except HTTPError:
            pass
        except (OSError, URLError):
            pass
        time.sleep(0.2)
    return False


def iniciar_runtime_alvo(
    entrada: EntradaE2ENormalizada,
    inspecao: ProjetoInspecionadoE2E,
    workspace_projeto: str | None,
    max_tentativas: int = 2,
) -> RuntimeAlvoE2E:
    """Inicia somente perfis locais conhecidos e sempre em loopback."""

    if inspecao.perfil_inicializacao != "uvicorn" or not inspecao.entrypoint:
        return RuntimeAlvoE2E(
            status="nao_gerenciado",
            base_url=entrada.base_url,
            logs=["O perfil do sistema alvo não possui inicializador controlado."],
        )
    if not _ENTRYPOINT_UVICORN.fullmatch(inspecao.entrypoint):
        return RuntimeAlvoE2E(
            status="bloqueado",
            logs=["Entrypoint Uvicorn fora do formato permitido."],
        )

    workspace, erros = _resolver_workspace(workspace_projeto, entrada)
    if workspace is None:
        return RuntimeAlvoE2E(status="bloqueado", logs=erros)

    max_tentativas = max(1, min(int(max_tentativas), 3))
    creationflags = (
        subprocess.CREATE_NO_WINDOW
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW")
        else 0
    )
    logs: list[str] = []
    rotas_esperadas = {rota.rota for rota in inspecao.rotas}
    for tentativa in range(1, max_tentativas + 1):
        porta = _porta_loopback_livre()
        base_url = f"http://127.0.0.1:{porta}"
        argv = [
            sys.executable,
            "-m",
            "uvicorn",
            inspecao.entrypoint,
            "--host",
            "127.0.0.1",
            "--port",
            str(porta),
        ]
        try:
            processo = subprocess.Popen(
                argv,
                cwd=workspace,
                env=_ambiente_minimo_runtime(workspace),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                shell=False,
                creationflags=creationflags,
            )
        except OSError as exc:
            logs.append(f"Tentativa {tentativa}: falha ao iniciar Uvicorn: {exc}")
            continue

        if _runtime_responde(base_url, processo, rotas_esperadas):
            logs.append(
                f"Tentativa {tentativa}: runtime e rotas validados em loopback."
            )
            return RuntimeAlvoE2E(
                status="pronto",
                base_url=base_url,
                iniciado_pelo_agente=True,
                workspace=str(workspace),
                comando=argv,
                logs=logs,
                tentativas=tentativa,
                _processo=processo,
            )

        codigo_saida = processo.poll()
        if codigo_saida is None:
            processo.terminate()
            try:
                processo.wait(timeout=5)
            except subprocess.TimeoutExpired:
                processo.kill()
                processo.wait(timeout=5)
        logs.append(
            f"Tentativa {tentativa}: healthcheck ou rotas não confirmados "
            f"(codigo_saida={codigo_saida})."
        )

    return RuntimeAlvoE2E(
        status="erro_inicializacao",
        workspace=str(workspace),
        logs=logs,
        tentativas=max_tentativas,
        encerrado=True,
    )
