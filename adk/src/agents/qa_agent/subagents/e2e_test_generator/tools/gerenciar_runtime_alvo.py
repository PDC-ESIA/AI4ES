"""Inicialização controlada do sistema alvo para execução E2E local."""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from shared.workspace import get_agent_workspace

from ..schemas import EntradaE2ENormalizada, ProjetoInspecionadoE2E

_RAIZ_ADK = Path(__file__).resolve().parents[6]
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

    def encerrar(self) -> None:
        # O executor já removeu o contêiner; não existe processo no host.
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
    raizes = {get_agent_workspace(nome).resolve() for nome in ("coder", "e2e_test_generator")}
    if not any(_esta_contido(candidato, raiz) for raiz in raizes):
        return None, ["workspace_projeto fora das raízes permitidas."]
    if not candidato.is_dir():
        return None, ["workspace_projeto não existe ou não é um diretório."]
    return candidato, []


def iniciar_runtime_alvo(
    entrada: EntradaE2ENormalizada,
    inspecao: ProjetoInspecionadoE2E,
    workspace_projeto: str | None,
    max_tentativas: int = 2,
) -> RuntimeAlvoE2E:
    """Prepara o alvo; sua inicialização só ocorre dentro do sandbox E2E."""
    if inspecao.perfil_inicializacao != "uvicorn" or not inspecao.entrypoint:
        return RuntimeAlvoE2E(status="bloqueado", logs=[
            "E2E isolado exige alvo Uvicorn gerenciado; serviços do host não são acessíveis."])
    if not _ENTRYPOINT_UVICORN.fullmatch(inspecao.entrypoint):
        return RuntimeAlvoE2E(status="bloqueado", logs=["Entrypoint não permitido."])
    workspace, erros = _resolver_workspace(workspace_projeto, entrada)
    if workspace is None:
        return RuntimeAlvoE2E(status="bloqueado", logs=["Workspace do alvo não permitido."])
    return RuntimeAlvoE2E(
        status="pronto", base_url="http://127.0.0.1:8765", workspace=str(workspace),
        comando=["uvicorn", inspecao.entrypoint],
        logs=["Alvo preparado; inicialização e healthcheck ocorrerão no contêiner."],
    )
