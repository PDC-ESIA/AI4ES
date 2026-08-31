"""Verificação de critérios de aceite por navegação real (PoC issue #394).

Orquestra, por código, a rodada de QA dentro do loop `coder ↔ executor`:

    critérios da Task → app no ar → spec Playwright → resultado por critério

Nada aqui é decidido por LLM exceto o conteúdo dos testes. Quando o QA roda, o
que ele roda e como o resultado vira evidência são decisões deterministicamente
tomadas aqui — mesma postura do resto da issue #394, que existe justamente para
tirar do modelo as decisões de controle do loop.

## De onde vêm os critérios

Do arquivo da Task (`<tasks_dir>/<task_id>.json`), a MESMA fonte que o estágio 1
do harness usa — e não do `run.json`, que o coder escreve. Isso importa para o
problema que este PoC ataca: o coder pode escolher COMO provar um critério, mas
nunca o que precisa ser provado, nem o texto do critério que será avaliado. A
garantia é estrutural e já existia; aqui ela é preservada, não construída.

## O portão de entrada

O QA só roda quando a base técnica já se provou, e a checagem é sobre o
`ExecutionReport` da rodada — não sobre a opinião de ninguém. Rodar antes disso
custaria um build inteiro para descobrir, via navegador, o que o harness já
disse de graça: que a aplicação não sobe. Quando o portão fecha, a rodada
devolve `ResultadoQA(executado=False)` e o fluxo segue com a evidência do
harness, exatamente como antes deste módulo existir.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Optional

import requests
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from shared.execution.qa_runtime import aplicacao_no_ar, healthcheck
from shared.execution.workspace_fingerprint import fingerprint_workspace
from shared.tools.coding_tools.criterios_aceite import (
    AcceptanceCriterion,
    canonizar_id,
    normalizar_criterios,
)
from shared.tools.coding_tools.harness_schemas import StageName, StageStatus
from shared.workspace import get_agent_workspace
from src.agents.qa_agent.subagents.e2e_test_generator.schemas import (
    EntradaE2ENormalizada,
)
from src.agents.qa_agent.subagents.e2e_test_generator.tools.executar_playwright import (
    executar_playwright,
)

from .agent import agent as qa_agent
from .schemas import EspecificacaoCriterios, ResultadoQA, TesteDeCriterio
from .spec import (
    escrever_spec,
    hash_do_spec,
    montar_evidencias,
    montar_spec,
    status_por_titulo,
    validar_corpo,
)

logger = logging.getLogger(__name__)

# Estágios que precisam ter concluído para valer a pena subir a app de novo. São
# os mesmos degraus que a nota técnica cobra antes dos critérios: sem build e
# sem aplicação no ar, não há interface a navegar.
_ESTAGIOS_EXIGIDOS = (
    StageName.IMPLANTACAO_ARTEFATO,
    StageName.INICIALIZACAO_APLICACAO,
)

# Quanto do HTML da página inicial acompanha o prompt. O suficiente para o QA
# reconhecer os elementos reais sem estourar o contexto com uma página grande.
_MAX_HTML = 12_000

# Perfil de comando aceito pelo runner do E2E (ver `_PERFIS_COMANDO_PERMITIDOS`).
_COMANDO_PLAYWRIGHT = "npx playwright test"

# Teto de tempo da suíte inteira de critérios, em segundos.
#
# ATENÇÃO ao que este valor faz: `executar_playwright` o usa nos DOIS relógios —
# o `timeout` do subprocess e o `globalTimeout` do Playwright. Não há margem
# entre eles, e quem vence é uma corrida. Na prática o Playwright vence (o
# relógio dele começa depois do boot do Node) e ele encerra escrevendo o
# relatório, com os testes cortados marcados como `interrupted` — que
# `montar_evidencias` lê como TESTE_NAO_EXECUTADO, nunca como reprovação. Se o
# subprocess vencer, não há relatório e a rodada vira `executado=False`. Os dois
# desfechos são seguros; nenhum inventa `nao_atendido` por estouro de tempo.
_TIMEOUT_SUITE = 240
_TIMEOUT_POR_TESTE_MS = 30_000


def _estagio_concluiu(report: dict, estagio: str) -> bool:
    """Se o estágio consta no report com status de sucesso."""
    for bruto in report.get("stages") or []:
        if isinstance(bruto, dict) and bruto.get("stage") == estagio:
            return bruto.get("status") == StageStatus.SUCESSO
    return False


def base_tecnica_comprovada(report: Any) -> bool:
    """Se a rodada chegou ao ponto em que navegar a aplicação faz sentido.

    Exige build concluído E aplicação inicializada. `INICIALIZACAO_APLICACAO`
    aparece como `pulado` para artefatos sem superfície de topo — que é
    exatamente o caso em que não há interface a navegar —, então cobrar sucesso
    aqui também descarta esses, sem precisar de um segundo teste.
    """
    if not isinstance(report, dict):
        return False
    return all(_estagio_concluiu(report, estagio) for estagio in _ESTAGIOS_EXIGIDOS)


def _carregar_criterios(tasks_dir: Path, task_id: str) -> list[AcceptanceCriterion]:
    """Lê os critérios do arquivo da Task — a mesma fonte do estágio 1."""
    caminho = tasks_dir / f"{task_id}.json"
    try:
        task = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        logger.warning("[QA] Task %s ilegível em %s: %s", task_id, caminho, erro)
        return []
    return normalizar_criterios(task.get("acceptance_criteria"))


def _html_da_pagina(base_url: str) -> str:
    """HTML da página inicial, truncado — contexto real para os localizadores."""
    try:
        resposta = requests.get(base_url, timeout=10)
        return resposta.text[:_MAX_HTML]
    except requests.RequestException as erro:
        logger.warning("[QA] Não foi possível ler o HTML de %s: %s", base_url, erro)
        return ""


def _montar_pedido(
    criterios: list[AcceptanceCriterion], base_url: str, html: str
) -> str:
    """O texto enviado ao agente de QA."""
    lista = "\n".join(f"- {c.id}: {c.description}" for c in criterios)
    return (
        f"URL da aplicação (já no ar): {base_url}\n\n"
        f"CRITÉRIOS DE ACEITE DESTA TASK:\n{lista}\n\n"
        f"HTML DA PÁGINA INICIAL:\n```html\n{html or '(não foi possível ler)'}\n```\n\n"
        "Produza um teste para cada critério que der para comprovar navegando, "
        "e declare em `nao_verificaveis` os que não derem."
    )


async def _pedir_especificacao(pedido: str) -> Optional[EspecificacaoCriterios]:
    """Invoca o agente de QA em runner isolado e devolve a especificação.

    Runner próprio, e não `AgentTool`, pelo mesmo motivo do `planner_wrapper` do
    qa_pipeline: a invocação parte de código, fora de um turno de LLM, e não há
    `ToolContext` a que se pendurar. A sessão isolada tem um efeito colateral
    desejável — o QA não enxerga o state do loop, então não pode ser influenciado
    pelo histórico de tentativas do coder.

    Returns:
        A especificação, ou `None` quando o agente falhou ou respondeu algo
        inaproveitável — caso em que a rodada de QA não acontece, e a evidência
        do harness segue valendo.
    """
    try:
        runner = Runner(
            app_name=qa_agent.name,
            agent=qa_agent,
            session_service=InMemorySessionService(),
        )
        sessao = await runner.session_service.create_session(
            app_name=qa_agent.name, user_id="cr-executor-qa", state={}
        )
        resposta = ""
        async for evento in runner.run_async(
            user_id=sessao.user_id,
            session_id=sessao.id,
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text=pedido)]
            ),
        ):
            if evento.content and evento.content.parts:
                for parte in evento.content.parts:
                    if parte.text:
                        resposta = parte.text
        await runner.close()
    except Exception as erro:  # noqa: BLE001 — QA indisponível não derruba a rodada
        logger.warning("[QA] Falha ao invocar o agente de QA: %s", erro)
        return None

    if not resposta.strip():
        logger.warning("[QA] O agente de QA respondeu vazio.")
        return None
    try:
        return EspecificacaoCriterios.model_validate_json(resposta)
    except ValidationError as erro:
        logger.warning("[QA] Resposta do QA fora do contrato: %s", erro)
        return None


def _filtrar_testes(
    especificacao: EspecificacaoCriterios, criterios: list[AcceptanceCriterion]
) -> tuple[list[TesteDeCriterio], dict[str, str]]:
    """Separa os testes aproveitáveis das recusas, com id canonizado.

    Duas checagens deterministicas, ambas sobre o que o LLM escreveu:

    1. O id precisa existir NA TASK. Mesma regra que `normalizar_mapa_de_testes`
       aplica ao mapa do coder: um id inventado não pode virar cobertura de um
       critério que não existe.
    2. O corpo precisa poder constituir prova (`validar_corpo`).

    Um id repetido mantém só o PRIMEIRO teste: dois testes para o mesmo critério
    colidiriam no mapa título ↔ critério, e o segundo sobrescreveria o primeiro
    de forma invisível.

    Returns:
        `(testes_aprovados, recusas_por_id)`.
    """
    validos = {c.id for c in criterios}
    aprovados = []
    recusas: dict[str, str] = {}
    vistos: set[str] = set()

    for teste in especificacao.testes:
        identificador = canonizar_id(teste.criterion_id)
        if identificador is None or identificador not in validos:
            logger.warning(
                "[QA] Teste descartado: criterion_id %r não existe nesta Task.",
                teste.criterion_id,
            )
            continue
        if identificador in vistos:
            logger.warning(
                "[QA] Teste descartado: %s já tinha teste nesta rodada.",
                identificador,
            )
            continue
        vistos.add(identificador)

        motivo = validar_corpo(teste.corpo)
        if motivo is not None:
            logger.warning("[QA] Teste de %s recusado: %s", identificador, motivo)
            recusas[identificador] = motivo
            continue
        aprovados.append(teste.model_copy(update={"criterion_id": identificador}))

    return aprovados, recusas


def _normalizar_nao_verificaveis(
    especificacao: EspecificacaoCriterios, criterios: list[AcceptanceCriterion]
) -> EspecificacaoCriterios:
    """Canoniza os ids declarados não verificáveis e descarta os inexistentes."""
    validos = {c.id for c in criterios}
    mantidos = []
    for item in especificacao.nao_verificaveis:
        identificador = canonizar_id(item.criterion_id)
        if identificador is not None and identificador in validos:
            mantidos.append(item.model_copy(update={"criterion_id": identificador}))
    return especificacao.model_copy(update={"nao_verificaveis": mantidos})


def _chave_de_reuso(
    criterios: list[AcceptanceCriterion], coder_dir: Path, base_url: str
) -> Optional[str]:
    """Identidade da situação que o spec verifica: código + critérios + URL.

    Mesma chave ⇒ o spec anterior continua válido e pode ser reexecutado.

    Returns:
        `None` quando a identidade não pôde ser estabelecida (fingerprint
        indisponível). `None` significa "não reuse E não guarde": guardar sob uma
        chave aleatória sobrescreveria um metadado válido, custando a
        reprodutibilidade também da rodada SEGUINTE por causa de uma falha
        transitória desta.
    """
    try:
        impressao = fingerprint_workspace(coder_dir)
    except Exception:  # noqa: BLE001 — sem identidade, sem reuso
        logger.warning(
            "[QA] Não foi possível calcular o fingerprint do workspace; o spec "
            "desta rodada não será reusado nem guardado."
        )
        return None
    partes = [
        base_url,
        impressao,
        *(f"{c.id}|{c.description}|{c.automatable}" for c in criterios),
    ]
    return hashlib.sha256("\n".join(partes).encode("utf-8")).hexdigest()


async def _obter_especificacao_e_spec(
    task_id: str,
    criterios: list[AcceptanceCriterion],
    base_url: str,
    html: str,
    coder_dir: Path,
):
    """Devolve a especificação e o spec desta rodada, REUSANDO quando possível.

    O reuso existe por causa da `loop_policy`, não por economia. A nota precisa
    ser reprodutível: mesma entrada, mesma nota. Se o QA escrevesse testes novos
    a cada rodada, o degrau de critérios oscilaria com o código PARADO — um
    localizador escolhido diferente, um `getByRole` no lugar de um `getByText` —
    e a política leria essa oscilação como progresso (zerando a tolerância de
    platô indefinidamente) ou como regressão. Com o código igual e os critérios
    iguais, o spec é o mesmo e a nota também.

    Quando o coder MEXE no código, a chave muda e o QA escreve de novo — que é o
    correto: a interface mudou, os localizadores podem ter mudado com ela.

    Returns:
        `(especificacao, testes, recusas, titulos, caminho_spec)`;
        `especificacao` é `None` quando o QA não produziu nada utilizável.
    """
    destino = get_agent_workspace("e2e_test_generator")
    chave = _chave_de_reuso(criterios, coder_dir, base_url)

    if chave is not None:
        guardado = _ler_spec_guardado(destino, task_id, chave)
        if guardado is not None:
            logger.info(
                "[QA] Task %s: reusando o spec da rodada anterior (código e "
                "critérios inalterados).",
                task_id,
            )
            return guardado

    pedido = _montar_pedido(criterios, base_url, html)
    especificacao = await _pedir_especificacao(pedido)
    if especificacao is None:
        return None, [], {}, {}, None

    especificacao = _normalizar_nao_verificaveis(especificacao, criterios)
    testes, recusas = _filtrar_testes(especificacao, criterios)
    if not testes:
        return especificacao, [], recusas, {}, None

    conteudo, titulos = montar_spec(
        testes, base_url, {c.id: c.description for c in criterios}
    )
    caminho_spec = await asyncio.to_thread(
        escrever_spec,
        destino,
        task_id,
        conteudo,
        chave,
        especificacao,
        recusas,
        titulos,
    )
    return especificacao, testes, recusas, titulos, caminho_spec


def _ler_spec_guardado(destino: Path, task_id: str, chave: str):
    """O spec da rodada anterior, se ele ainda vale para esta situação.

    Além da chave, confere que o `.spec.ts` em disco é EXATAMENTE o que gerou
    este metadado. As duas escritas não são atômicas entre si: se a segunda
    falhar, sobra um spec novo ao lado de um metadado velho, e reusar os títulos
    velhos faria nenhum teste casar — todo critério viraria
    `TESTE_NAO_EXECUTADO` e o degrau sairia da nota, silenciosamente.
    """
    try:
        guardado = json.loads(
            (destino / f"criterios_{task_id}.meta.json").read_text(encoding="utf-8")
        )
    except OSError, json.JSONDecodeError:
        return None
    if not isinstance(guardado, dict) or guardado.get("chave") != chave:
        return None

    caminho = destino / f"criterios_{task_id}.spec.ts"
    if not caminho.is_file():
        return None
    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except OSError:
        return None
    if hash_do_spec(conteudo) != guardado.get("hash_spec"):
        logger.warning(
            "[QA] Task %s: o spec em disco não corresponde ao metadado; "
            "gerando de novo em vez de reusar títulos que não casariam.",
            task_id,
        )
        return None

    try:
        especificacao = EspecificacaoCriterios.model_validate(
            guardado.get("especificacao")
        )
    except ValidationError:
        return None

    titulos = guardado.get("titulos")
    recusas = guardado.get("recusas")
    if not isinstance(titulos, dict) or not isinstance(recusas, dict):
        return None
    testes = [t for t in especificacao.testes if t.criterion_id in titulos]
    if not testes:
        return None
    return especificacao, testes, recusas, titulos, caminho


async def verificar_criterios_por_e2e(
    task_id: str,
    execution_report: Any,
    *,
    coder_dir: Optional[Path] = None,
    tasks_dir: Optional[Path] = None,
) -> ResultadoQA:
    """Verifica os critérios de aceite navegando a aplicação, se couber.

    Nunca levanta: cada motivo de não verificar vira `ResultadoQA(executado=
    False, motivo=...)`. Quem chama está no meio de uma rodada do loop, e uma
    exceção aqui custaria a rodada inteira por uma medida que é, por desenho,
    auxiliar.

    Args:
        task_id: Task da vez.
        execution_report: O `ExecutionReport` desta rodada, para o portão.
        coder_dir: Raiz do artefato do coder (default: workspace do `cr_coder`).
        tasks_dir: Onde vivem as Tasks (default: workspace do context engineer).

    Returns:
        `ResultadoQA` — com uma evidência por critério quando executou.
    """
    if not base_tecnica_comprovada(execution_report):
        return ResultadoQA(
            executado=False,
            motivo=(
                "Base técnica não comprovada nesta rodada (build ou "
                "inicialização da aplicação não concluíram): não há interface "
                "no ar para navegar."
            ),
        )

    coder_dir = coder_dir or get_agent_workspace("cr_coder")
    tasks_dir = tasks_dir or get_agent_workspace("cr_context_engineer")

    criterios = _carregar_criterios(tasks_dir, task_id)
    if not criterios:
        return ResultadoQA(
            executado=False,
            motivo=f"A Task {task_id} não declara critérios de aceite legíveis.",
        )

    # O ciclo de vida da aplicação é aberto e fechado em THREAD, e não com um
    # `with` direto: subir o artefato faz build (até 300s), `time.sleep` e HTTP
    # síncrono, e este código roda dentro de um `after_agent_callback` async.
    # Segurar o event loop por minutos travaria a sessão inteira do ADK. O
    # `finally` garante o fechamento com a mesma força que o `with` daria.
    gerenciador = aplicacao_no_ar(coder_dir)
    aplicacao = await asyncio.to_thread(gerenciador.__enter__)
    try:
        if not aplicacao.no_ar:
            return ResultadoQA(executado=False, motivo=aplicacao.motivo)

        base_url = aplicacao.base_url
        html = await asyncio.to_thread(_html_da_pagina, base_url)
        (
            especificacao,
            testes,
            recusas,
            titulos,
            caminho_spec,
        ) = await _obter_especificacao_e_spec(
            task_id, criterios, base_url, html, coder_dir
        )
        if especificacao is None:
            return ResultadoQA(
                executado=False,
                motivo="O agente de QA não produziu uma especificação utilizável.",
            )

        if not testes:
            # Sem teste algum não há execução, mas AINDA há o que registrar: os
            # critérios recusados e os declarados não verificáveis explicam por
            # que a cobertura ficou em aberto. Devolver a evidência aqui é o que
            # diferencia "o QA olhou e não conseguiu" de "o QA não rodou".
            return ResultadoQA(
                executado=True,
                motivo="Nenhum teste de navegação aproveitável foi produzido.",
                evidencias=montar_evidencias(
                    criterios, especificacao, {}, {}, recusas, base_url
                ),
            )

        resultado = await asyncio.to_thread(
            executar_playwright,
            EntradaE2ENormalizada(
                base_url=base_url,
                comando_execucao=_COMANDO_PLAYWRIGHT,
                ambiente_execucao={
                    "timeout_segundos": _TIMEOUT_SUITE,
                    "timeout_teste_ms": _TIMEOUT_POR_TESTE_MS,
                },
            ),
            str(caminho_spec),
        )

        status = _ler_status(resultado)
        if status is None:
            return ResultadoQA(
                executado=False,
                motivo=(
                    "O Playwright não produziu relatório utilizável "
                    f"(status: {resultado.status}). "
                    + "; ".join(resultado.logs_resumidos[:3])
                ),
                spec_path=str(caminho_spec),
            )

        # A aplicação precisa continuar de pé DEPOIS da suíte para que uma falha
        # conte como "a aplicação não faz o que o critério pede". Se ela morreu
        # no meio, os testes falharam por infraestrutura, e marcá-los como
        # `nao_atendido` reprovaria a entrega por um defeito do ambiente —
        # exatamente o tipo de teto artificial que este desenho evita.
        viva, _ = await asyncio.to_thread(
            healthcheck, base_url, aplicacao.manifest.healthcheck or "/"
        )
        if not viva:
            return ResultadoQA(
                executado=False,
                motivo=(
                    "A aplicação parou de responder durante a suíte de "
                    "navegação; os resultados não distinguem falha da entrega de "
                    "falha do ambiente."
                ),
                spec_path=str(caminho_spec),
            )

        logger.info(
            "[QA] Task %s: %d critério(s) verificado(s) por navegação "
            "(%d aprovado(s), %d falho(s)).",
            task_id,
            len(testes),
            resultado.testes_aprovados,
            resultado.testes_falhos,
        )
        return ResultadoQA(
            executado=True,
            evidencias=montar_evidencias(
                criterios, especificacao, titulos, status, recusas, base_url
            ),
            spec_path=str(caminho_spec),
        )
    finally:
        # SÍNCRONO de propósito, e é a única coisa neste módulo que segura o
        # event loop de caso pensado. Sob `CancelledError`, um
        # `await asyncio.to_thread(...)` aqui pode nunca chegar a ser agendado —
        # o sandbox vazaria e a porta ficaria presa. E a consequência não seria
        # uma rodada perdida: a guarda `_porta_ja_responde` passaria a recusar o
        # QA em TODAS as rodadas seguintes por "porta ocupada", desligando a
        # verificação em silêncio. O cleanup é curto (matar o grupo de processos
        # e apagar o diretório temporário); bloquear por ele é barato perto
        # disso.
        gerenciador.__exit__(None, None, None)


def _ler_status(resultado) -> Optional[dict[str, str]]:
    """Lê o relatório JSON do Playwright e devolve título → status.

    `None` quando o relatório não existe ou não é legível — o que significa que
    a suíte não chegou a rodar (runtime ausente, spec que não compila). Isso é
    diferente de "rodou e falhou", e precisa continuar diferente: uma suíte que
    não rodou não reprova critério nenhum.
    """
    if not resultado.arquivo_relatorio:
        return None
    try:
        bruto = json.loads(
            Path(resultado.arquivo_relatorio).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as erro:
        logger.warning("[QA] Relatório do Playwright ilegível: %s", erro)
        return None
    status = status_por_titulo(bruto)
    return status or None
