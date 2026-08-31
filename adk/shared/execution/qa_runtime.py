"""Instância própria da aplicação do coder, para o QA navegar (PoC issue #394).

Sobe o artefato do coder — build, serviço em segundo plano, healthcheck — e
entrega uma `base_url` viva a quem precisa dirigir a aplicação por fora do
processo (o Playwright do QA, hoje). O ciclo de vida é um context manager: o
sandbox é sempre encerrado na saída, inclusive por exceção.

## Por que uma instância PRÓPRIA, e não a do harness

O sandbox do harness nasce no estágio 1 (`_estagio_preparacao`) e morre no
`finally` de `executar_harness_validacao` — a função inteira é uma unidade
fechada, que cria e destrói o seu próprio ambiente. Quando o QA roda, depois que
o harness retornou, aquele sandbox já não existe.

Reaproveitá-lo exigiria que o harness segurasse o sandbox vivo à espera de um
agente externo terminar. Isso quebraria a propriedade que faz dele um sensor
confiável: hoje ele não depende de LLM nenhum para decidir quando encerrar, e
uma etapa de QA travada não tem como vazar para dentro do ciclo de vida dele.
Pagar um build a mais por rodada é o preço de manter essa fronteira intacta.

Consequência aceita: o custo por rodada de QA é o de um build completo (até
`_BUILD_TIMEOUT`). É por isso que quem chama só deve fazê-lo depois que a base
técnica já se provou — ver `qa_criterios.verificacao`.

## O que este módulo NÃO faz

Não julga nada e não conhece critério de aceite: entrega uma URL ou um motivo
para não haver uma. Toda leitura sobre o que a aplicação faz pertence a quem
consome a URL.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import requests

from shared.execution.manifest import ManifestError, RunManifest, load_manifest
from shared.execution.sandbox import create_sandbox
from shared.tools.coding_tools import harness_docker as hd

logger = logging.getLogger(__name__)

# Nome do manifesto na raiz do artefato — o mesmo contrato que o harness lê.
_MANIFEST_FILENAME = "run.json"

# Tetos de tempo. Iguais aos do harness de propósito: é o MESMO artefato sendo
# construído e iniciado, e divergir aqui faria o QA falhar por timeout em um
# projeto que o harness constrói sem problema — um falso negativo caro e
# confuso, porque a evidência apontaria para o critério e não para o teto.
_BUILD_TIMEOUT = 300


@dataclass(frozen=True)
class AplicacaoNoAr:
    """O resultado de tentar subir a aplicação para inspeção externa.

    Attributes:
        base_url: URL viva da aplicação, ou `None` quando não subiu.
        motivo: Por que não subiu; vazio quando subiu. É texto para registro em
            evidência, nunca um código sobre o qual se ramifique lógica.
        manifest: O manifesto lido, quando a leitura chegou a acontecer.
    """

    base_url: Optional[str]
    motivo: str = ""
    manifest: Optional[RunManifest] = None

    @property
    def no_ar(self) -> bool:
        return self.base_url is not None


def _porta_ja_responde(base_url: str, rota: str) -> bool:
    """Se alguém JÁ atende nesta porta antes de o QA subir o serviço.

    Guarda contra o pior modo de falha deste módulo: um serviço remanescente de
    uma rodada anterior (cleanup que não matou o processo, porta ainda presa)
    responderia ao healthcheck, e o QA navegaria o CÓDIGO ANTIGO acreditando ser
    o novo — reprovando ou aprovando critérios sobre um artefato que não é o que
    o coder acabou de escrever. Um falso sinal desses é pior que não medir.

    Uma única tentativa, sem retry: a pergunta é "há algo aqui AGORA", e retry
    só serviria para dar tempo de alguém subir — o oposto do que se quer saber.
    """
    try:
        requests.get(f"{base_url}{rota}", timeout=hd._HTTP_HEALTHCHECK_TIMEOUT)
    except requests.RequestException:
        return False
    return True


def healthcheck(base_url: str, rota: str) -> tuple[bool, str]:
    """Espera a aplicação responder, com os mesmos retries do harness.

    Returns:
        `(viva, ultimo_erro)`. Um HTTP >= 400 conta como não viva: a aplicação
        está de pé mas não serve, e navegar nela produziria falha de critério
        onde o problema é de inicialização.
    """
    url = f"{base_url}{rota}"
    ultimo_erro = ""
    for tentativa in range(1, hd._HEALTHCHECK_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=hd._HTTP_HEALTHCHECK_TIMEOUT)
            if resp.status_code < 400:
                return True, ""
            return False, f"A aplicação respondeu HTTP {resp.status_code} em {url}."
        except requests.RequestException as erro:
            ultimo_erro = f"A aplicação não respondeu em {url} ({erro})."
            if tentativa < hd._HEALTHCHECK_RETRIES:
                time.sleep(hd._HEALTHCHECK_RETRY_INTERVAL)
    return False, ultimo_erro


@contextmanager
def aplicacao_no_ar(coder_dir: Path) -> Iterator[AplicacaoNoAr]:
    """Sobe o artefato do coder e entrega a URL enquanto o bloco durar.

    Só faz sentido para `surface="service"`: um artefato sem serviço de rede não
    tem o que navegar, e o QA de interface não se aplica a ele. Nesse caso o
    context manager entrega `AplicacaoNoAr(base_url=None, motivo=...)` sem gastar
    build nenhum — a não-aplicabilidade é barata e explícita.

    Toda falha vira `motivo`, nunca exceção: quem chama está no meio de uma
    rodada do loop, e derrubá-la por um build quebrado custaria a rodada inteira
    quando a resposta honesta é "não deu para verificar por interface".

    Args:
        coder_dir: Raiz do artefato do coder (onde vive o `run.json`).

    Yields:
        `AplicacaoNoAr` — com `base_url` viva, ou com o motivo de não haver uma.
    """
    manifest_path = coder_dir / _MANIFEST_FILENAME
    try:
        manifest = load_manifest(manifest_path)
    except ManifestError as erro:
        yield AplicacaoNoAr(None, f"Manifesto de execução inutilizável: {erro}")
        return

    if manifest.surface != "service":
        yield AplicacaoNoAr(
            None,
            (
                f"O artefato declara surface='{manifest.surface}': não expõe "
                "interface navegável, então não há o que verificar por E2E."
            ),
            manifest,
        )
        return

    base_url = f"http://localhost:{manifest.port}"
    rota_saude = manifest.healthcheck or "/"

    # ANTES de qualquer build: se alguém já atende nesta porta, não há o que
    # fazer aqui, e descobrir isso depois de construir o artefato desperdiçaria
    # um build inteiro (até `_BUILD_TIMEOUT`) para chegar à mesma conclusão.
    if _porta_ja_responde(base_url, rota_saude):
        yield AplicacaoNoAr(
            None,
            (
                f"A porta {manifest.port} já estava ocupada antes de o QA subir "
                "o serviço (provável processo remanescente de uma rodada "
                "anterior). Verificar por E2E aqui arriscaria navegar um "
                "artefato antigo."
            ),
            manifest,
        )
        return

    sandbox = None
    try:
        try:
            sandbox = create_sandbox(
                manifest.sandbox,
                port=manifest.port,
                workdir_subpath=manifest.workdir,
            )
            sandbox.setup(coder_dir)
        except Exception as erro:  # noqa: BLE001 — infraestrutura vira motivo
            logger.warning("[QA_RUNTIME] Falha ao preparar o sandbox: %s", erro)
            yield AplicacaoNoAr(
                None, f"Não foi possível preparar o sandbox do QA: {erro}", manifest
            )
            return

        for comando in manifest.build:
            resultado = sandbox.exec(
                comando, timeout=_BUILD_TIMEOUT, env=dict(manifest.env) or None
            )
            if resultado.timed_out or resultado.exit_code not in (0, None):
                detalhe = (
                    f"excedeu {_BUILD_TIMEOUT}s"
                    if resultado.timed_out
                    else f"retornou exit={resultado.exit_code}"
                )
                yield AplicacaoNoAr(
                    None,
                    f"O build do QA falhou: {comando!r} {detalhe}.",
                    manifest,
                )
                return

        try:
            sandbox.start_service(manifest.run, env=dict(manifest.env) or None)
        except Exception as erro:  # noqa: BLE001 — mesma razão do setup
            logger.warning("[QA_RUNTIME] Falha ao iniciar o serviço: %s", erro)
            yield AplicacaoNoAr(
                None, f"Não foi possível iniciar o serviço para o QA: {erro}", manifest
            )
            return

        time.sleep(hd._STARTUP_GRACE_PERIOD)
        viva, ultimo_erro = healthcheck(base_url, rota_saude)
        if not viva:
            yield AplicacaoNoAr(None, ultimo_erro, manifest)
            return

        logger.info("[QA_RUNTIME] Aplicação do QA no ar em %s.", base_url)
        yield AplicacaoNoAr(base_url, "", manifest)
    finally:
        if sandbox is not None:
            try:
                sandbox.cleanup()
            except Exception as erro:  # noqa: BLE001 — limpeza não derruba a rodada
                logger.warning("[QA_RUNTIME] Falha ao limpar o sandbox do QA: %s", erro)
