"""Playwright e aplicação alvo compartilham um contêiner sem rede externa."""
from pathlib import Path
import time

from shared.qa_sandbox import executar_isolado
from shared.security import detectar_credenciais, detectar_riscos_spec_ts
from shared.workspace import get_agent_workspace
from ..schemas import EntradaE2ENormalizada, ResultadoExecucaoE2E
from .gerenciar_runtime_alvo import RuntimeAlvoE2E


def executar_playwright(entrada: EntradaE2ENormalizada, arquivo_spec: str,
                       runtime_alvo: RuntimeAlvoE2E | None = None) -> ResultadoExecucaoE2E:
    inicio = time.monotonic()
    try:
        if (entrada.comando_execucao or "").strip().lower() not in {
            "playwright test", "npx playwright test", "pnpm exec playwright test", "npm run e2e:test"
        }:
            raise ValueError("Perfil inválido")
        arquivo = Path(arquivo_spec).resolve(strict=True)
        raiz = get_agent_workspace("e2e_test_generator").resolve()
        if not arquivo.is_relative_to(raiz) or not arquivo.name.endswith(".spec.ts"):
            raise ValueError("Spec fora do workspace")
        codigo = arquivo.read_text(encoding="utf-8")
        if detectar_riscos_spec_ts(codigo) or detectar_credenciais(codigo):
            raise ValueError("Spec inseguro")
        if runtime_alvo is None or not runtime_alvo.workspace or len(runtime_alvo.comando) != 2:
            raise ValueError("Alvo isolado não preparado")
        projeto = Path(runtime_alvo.workspace).resolve(strict=True)
        if not any(projeto.is_relative_to(get_agent_workspace(nome).resolve())
                   for nome in ("coder", "e2e_test_generator")):
            raise ValueError("Alvo fora do workspace")
        resultado = executar_isolado(
            arquivo.parent, arquivo.name, modo="playwright", projeto=projeto,
            entrypoint=runtime_alvo.comando[1], timeout=120,
        )
        passou, falhou, pulou = (resultado[k] for k in ("passed", "failed", "skipped"))
        return ResultadoExecucaoE2E(
            status="aprovado" if resultado["exit_code"] == 0 and passou > 0 and falhou == 0 else "falhou",
            comando="qa-sandbox playwright", codigo_saida=resultado["exit_code"],
            duracao_ms=int((time.monotonic() - inicio) * 1000),
            testes_executados=passou + falhou + pulou,
            testes_aprovados=passou, testes_falhos=falhou, testes_pulados=pulou,
            logs_resumidos=["Execução isolada concluída; logs, imagens e código bruto não são exportados."],
        )
    except Exception:
        return ResultadoExecucaoE2E(status="bloqueado_infraestrutura", logs_resumidos=[
            "Execução bloqueada: requer sandbox disponível, spec permitido e alvo gerenciado no contêiner."])
