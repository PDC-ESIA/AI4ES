"""Montagem e leitura determinística do spec Playwright do QA (issue #394).

Tudo o que dá para garantir sem perguntar a um LLM está aqui: o que o agente de
QA escreve é só o CORPO de cada teste, e este módulo decide se aquele corpo é
aceitável, monta o arquivo em volta dele e traduz o resultado da execução de
volta para o vocabulário de critérios do harness.

A divisão é a mesma que o resto do fluxo já usa entre o harness e o validador: o
LLM contribui o julgamento que só ele consegue dar (como comprovar este critério
nesta interface), e o código mantém as invariantes.

## Por que existe um portão sobre o código gerado

O problema que motivou este PoC é que o coder escrevia os testes do sistema que
ele mesmo implementou. Trocar o autor resolve o conflito de interesse, mas não
resolve sozinho o teste que passa sem provar nada — um `expect(true).toBe(true)`
é tão vazio escrito pelo QA quanto escrito pelo coder.

`validar_corpo` recusa, deterministicamente, os corpos que não podem constituir
prova: sem interação com a página, sem asserção, ou com a rede interceptada. O
último é o mais importante e o menos óbvio: um `page.route(...)` deixa o teste
passar contra uma resposta forjada pelo próprio teste, o que reintroduz por
outra via exatamente o vício que este desenho existe para eliminar.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Iterator, Optional

from shared.tools.coding_tools.criterios_aceite import AcceptanceCriterion
from shared.tools.coding_tools.harness_schemas import (
    CriterionEvidence,
    CriterionOutcome,
)

from .schemas import EspecificacaoCriterios, TesteDeCriterio

logger = logging.getLogger(__name__)

# Separador entre o id do critério e o título no nome do teste. Escolhido por
# não aparecer em texto de critério e por sobreviver ao relatório JSON do
# Playwright sem escaping — é ele que permite casar teste ↔ critério na volta.
SEPARADOR_TITULO = " :: "

# Métodos que deixam o teste de exercitar a aplicação real, casados em QUALQUER
# receptor (`page.`, `page.context().`, um alias `p.`) porque restringi-los a
# `page.` deixava passar `page.context().route(...)` e `const p = page; p.route(...)`
# — as duas formas mais óbvias de contornar a proibição.
_METODOS_QUE_FORJAM_A_APLICACAO = (
    "route",
    "routeFromHAR",
    "routeWebSocket",
    "unroute",
    "unrouteAll",
    "setContent",
    "evaluate",
    "evaluateHandle",
    "waitForFunction",
    "exposeFunction",
    "exposeBinding",
    "addInitScript",
    "addScriptTag",
    "addStyleTag",
    # `$eval`/`$$eval` fazem literalmente o que `evaluate` faz; bloquear um e
    # deixar os outros passar seria arbitrário. O `$` é escapado no regex.
    r"\$eval",
    r"\$\$eval",
)

# Construções recusadas no corpo de um teste, com o motivo pelo qual cada uma
# invalida a prova. Recusar é sempre mais seguro que corrigir: o QA tem outra
# rodada para reescrever, e um corpo "consertado" por regex viraria um teste que
# ninguém escreveu de fato.
_CONSTRUCOES_PROIBIDAS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"[.\[]\s*['\"`]?(?:"
            + "|".join(_METODOS_QUE_FORJAM_A_APLICACAO)
            + r")['\"`]?\s*\]?\s*\(",
            re.IGNORECASE,
        ),
        "intercepta a rede ou injeta conteúdo próprio (route/setContent/evaluate "
        "e afins): o teste passaria contra algo forjado por ele mesmo, sem "
        "exercitar a aplicação",
    ),
    (
        # Acesso computado seguido de chamada — `page[m](...)`, `page['ro'+'ute']
        # (...)`, `page['route'](...)`. Nenhuma lista de nomes alcança essas
        # formas, porque o nome do método só existe em tempo de execução. Um
        # corpo de teste legítimo nunca precisa chamar método por índice, então
        # recusar a CONSTRUÇÃO inteira fecha a classe toda de uma vez.
        re.compile(r"\w\s*\[[^\]\n]*\]\s*\("),
        "chama método por acesso computado (`obj[...](...)`): a forma esconde "
        "qual método está sendo chamado, e nenhum teste legítimo precisa dela",
    ),
    (
        # Qualquer URL absoluta no corpo, em qualquer forma. Checar só o
        # argumento literal de `goto` deixava passar
        # `const u = 'https://x'; page.goto(u)`.
        re.compile(r"://"),
        "cita uma URL absoluta: o teste precisa exercitar a aplicação sob teste, "
        "sempre por caminho relativo (`page.goto('/...')`)",
    ),
    (
        re.compile(r"\bimport\s*[({]|\bimport\s+[\w*{]"),
        "declara import: o cabeçalho do arquivo é montado por código",
    ),
    (
        re.compile(r"\brequire\s*\("),
        "usa require: o corpo do teste não carrega módulos",
    ),
    (
        re.compile(r"\btest\s*(?:\.\w+)?\s*\(|\bdescribe\s*\("),
        "declara outro test(): o wrapper do teste é montado por código",
    ),
    (
        re.compile(r"\.(?:skip|fixme|only)\s*\("),
        "usa skip/fixme/only: um teste que não roda não comprova critério algum",
    ),
    (
        re.compile(r"\bprocess\.env\b"),
        "lê variáveis de ambiente: a URL da aplicação é injetada por código",
    ),
)

# Um corpo precisa PELO MENOS interagir com a página e afirmar algo sobre ela.
# É um piso grosseiro de propósito: não tenta julgar se a asserção é boa (isso
# exigiria entender o critério, que é justamente o trabalho do LLM), só recusa o
# que comprovadamente não prova nada.
_EXIGE_PAGINA = re.compile(r"\bpage\s*\.\s*\w+")
_EXIGE_ASSERCAO = re.compile(r"\bexpect\s*\(")

# Comentários de linha e de bloco. Casados JUNTO com os literais de string
# porque um `//` dentro de string não é comentário — varrer as alternativas de
# uma vez só resolve essa ambiguidade.
_COMENTARIOS = re.compile(
    r"('(?:\\.|[^'\\])*')"
    r'|("(?:\\.|[^"\\])*")'
    r"|(`(?:\\.|[^`\\])*`)"
    r"|(//[^\n]*)"
    r"|(/\*.*?\*/)",
    re.DOTALL,
)

_STRINGS = re.compile(
    r"'(?:\\.|[^'\\])*'" r'|"(?:\\.|[^"\\])*"' r"|`(?:\\.|[^`\\])*`",
    re.DOTALL,
)


def _apagar(texto: str) -> str:
    """Substitui por espaços, preservando as quebras de linha."""
    return re.sub(r"[^\n]", " ", texto)


def _sem_comentarios(corpo: str) -> str:
    """Apaga SÓ os comentários; os literais de string continuam legíveis.

    Passo intermediário de `_sem_comentarios_e_strings`. Nenhuma PROIBIÇÃO roda
    sobre este texto — elas rodam sobre o corpo cru, porque esta limpeza é
    enganável por um literal de expressão regular contendo `/*` (ver
    `validar_corpo`). Aqui a limpeza serve só para as exigências positivas, onde
    limpar demais causa recusa e nunca aceitação indevida.
    """
    return _COMENTARIOS.sub(
        lambda m: _apagar(m.group(0)) if m.group(4) or m.group(5) else m.group(0),
        corpo,
    )


def _sem_comentarios_e_strings(corpo: str) -> str:
    """Apaga comentários E literais, deixando só a estrutura do código.

    É sobre este texto que as EXIGÊNCIAS positivas rodam (`page.`, `expect(`):
    sem isso, `// page.goto('/')` num comentário — ou a string `'page.goto e
    expect('` — satisfariam a exigência de interagir com a página, e um corpo
    inteiramente comentado passaria no portão.
    """
    return _STRINGS.sub(lambda m: _apagar(m.group(0)), _sem_comentarios(corpo))


def validar_corpo(corpo: str) -> Optional[str]:
    """O motivo pelo qual este corpo de teste não serve como prova, ou `None`.

    O portão é uma barreira contra o teste VAZIO, não contra um QA adversário:
    um modelo determinado a burlá-lo consegue (nada aqui interpreta semântica).
    O que ele garante é que as formas ÓBVIAS de produzir um teste que passa sem
    provar nada — comentar tudo, interceptar a rede, injetar o próprio HTML,
    navegar para fora da aplicação — sejam recusadas de forma determinística.

    Returns:
        `None` quando o corpo é aceitável; caso contrário, o texto do motivo —
        que vira evidência, para que a recusa seja auditável e o QA possa
        corrigir na rodada seguinte.
    """
    if not corpo or not corpo.strip():
        return "o corpo do teste veio vazio"

    # As PROIBIÇÕES rodam sobre o corpo CRU, sem nenhuma limpeza prévia.
    #
    # Foi a lição de uma tentativa anterior: limpar comentários antes exige
    # entender a sintaxe de JavaScript, e um literal de expressão regular
    # contendo `/*` — `const a = /[/*]/;` — enganava o limpador, que apagava
    # como "comentário de bloco" o código real que vinha depois. Um
    # `page.route(...)` escondido assim atravessava o portão inteiro.
    #
    # Sobre o texto cru não há o que enganar. O preço é o falso positivo: um
    # comentário que MENCIONE `page.route(` ou uma URL absoluta é recusado junto.
    # É o lado certo do erro — uma recusa custa uma rodada; um teste que forja a
    # aplicação custa a confiança na nota inteira.
    for padrao, motivo in _CONSTRUCOES_PROIBIDAS:
        if padrao.search(corpo):
            return motivo

    # As EXIGÊNCIAS positivas, ao contrário, rodam sobre o texto SEM comentários
    # nem strings: aqui a limpeza excessiva só pode causar recusa (a direção
    # segura), nunca aceitação indevida.
    codigo = _sem_comentarios_e_strings(corpo)
    if not codigo.strip():
        return "o corpo do teste não tem código (só comentários ou texto)"

    if not _EXIGE_PAGINA.search(codigo):
        return "não interage com a página (nenhuma chamada a `page.`)"
    if not _EXIGE_ASSERCAO.search(codigo):
        return "não afirma nada sobre o resultado (nenhum `expect(`)"
    return None


def titulo_do_teste(criterion_id: str, titulo: str) -> str:
    """O título com que o teste aparece no relatório do Playwright.

    O id vem PREFIXADO porque é ele que reidentifica o critério na volta: o
    relatório do Playwright devolve títulos, não os objetos que os originaram.
    """
    limpo = " ".join((titulo or "").split()).replace(SEPARADOR_TITULO, " - ")
    return f"{criterion_id}{SEPARADOR_TITULO}{limpo or 'critério de aceite'}"


def _escapar_para_literal(valor: str) -> str:
    """Escapa uma string para interpolação segura em literal TypeScript."""
    return valor.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


def montar_spec(
    testes: list[TesteDeCriterio],
    base_url: str,
    descricoes: Optional[dict[str, str]] = None,
) -> tuple[str, dict[str, str]]:
    """Monta o arquivo `.spec.ts` completo a partir dos corpos aprovados.

    A `base_url` é gravada como CONSTANTE no arquivo, e não lida do ambiente: o
    runner (`executar_playwright`) monta o env do processo Node a partir de uma
    allowlist fixa, então uma variável nova não chegaria ao teste. Assar a URL no
    arquivo também deixa o spec auditável por si só — quem o ler depois sabe
    contra o que ele rodou.

    Args:
        descricoes: Id → texto do critério, usado quando o QA deixa o `titulo`
            em branco. Numa execução real o modelo omitiu esse campo em TODOS os
            testes, e o relatório saía com três "critério de aceite" idênticos —
            legível para o código (os ids diferem), inútil para quem audita.

    Returns:
        `(conteudo, titulos_por_criterio)` — o mapa é o vínculo título ↔ critério
        usado para ler o relatório de volta.
    """
    descricoes = descricoes or {}
    titulos: dict[str, str] = {}
    blocos: list[str] = []

    for teste in testes:
        titulo = titulo_do_teste(
            teste.criterion_id,
            teste.titulo or descricoes.get(teste.criterion_id, ""),
        )
        titulos[teste.criterion_id] = titulo
        corpo_indentado = "\n".join(
            f"  {linha}" if linha.strip() else "" for linha in teste.corpo.splitlines()
        )
        blocos.append(
            f"test('{_escapar_para_literal(titulo)}', async ({{ page }}) => {{\n"
            f"{corpo_indentado}\n"
            f"}});"
        )

    conteudo = (
        "// Gerado pelo QA de critérios de aceite (PoC issue #394).\n"
        "// Um teste por critério; o id no título é o vínculo com a Task.\n"
        "import { test, expect } from '@playwright/test';\n\n"
        f"const BASE_URL = '{_escapar_para_literal(base_url)}';\n\n"
        "test.use({ baseURL: BASE_URL });\n\n" + "\n\n".join(blocos) + "\n"
    )
    return conteudo, titulos


# ---------------------------------------------------------------------------
# Leitura do relatório JSON do Playwright
# ---------------------------------------------------------------------------

# Status por teste no relatório do Playwright → o que ele significa como prova.
# `flaky` conta como falha: um teste que só passa às vezes não comprova nada de
# forma estável, e tratá-lo como atendido deixaria a nota oscilar sozinha entre
# rodadas sem que o código mudasse.
_STATUS_ATENDIDO = "expected"
_STATUS_NAO_ATENDIDO = ("unexpected", "flaky")

# Severidade relativa dos status, para consolidar execuções repetidas do mesmo
# teste. Quanto maior, "pior" — e o pior vence. O desconhecido fica ACIMA do
# aprovado e ABAIXO da falha: um status que não sabemos ler não pode virar
# comprovação, mas também não é evidência de que a aplicação falhou.
_SEVERIDADE = {"expected": 0, "skipped": 1, "flaky": 3, "unexpected": 3}
_SEVERIDADE_DESCONHECIDA = 2


def _severidade(status: str) -> int:
    return _SEVERIDADE.get(status, _SEVERIDADE_DESCONHECIDA)


def _percorrer_suites(no: Any) -> Iterator[tuple[str, str]]:
    """Percorre a árvore do relatório rendendo `(titulo_do_teste, status)`."""
    if not isinstance(no, dict):
        return
    for spec in no.get("specs") or []:
        if not isinstance(spec, dict):
            continue
        titulo = spec.get("title")
        if not isinstance(titulo, str):
            continue
        for teste in spec.get("tests") or []:
            if isinstance(teste, dict) and isinstance(teste.get("status"), str):
                yield titulo, teste["status"]
    for suite in no.get("suites") or []:
        yield from _percorrer_suites(suite)


def status_por_titulo(relatorio: Any) -> dict[str, str]:
    """Indexa o relatório do Playwright por título de teste.

    Lê o relatório BRUTO em vez de reaproveitar as contagens agregadas de
    `ResultadoExecucaoE2E`: o agregado diz quantos falharam, não QUAIS — e a lista
    de falhas de lá omite os testes pulados, que aqui precisam ser distinguidos
    de aprovados. Confundir os dois faria um teste que nem rodou contar como
    critério atendido, que é o erro mais caro possível nesta tradução.
    """
    encontrado: dict[str, str] = {}
    for titulo, status in _percorrer_suites(relatorio):
        # Um mesmo título com mais de um resultado (retry, projetos múltiplos):
        # o pior status prevalece — comprovação exige que TODAS as execuções
        # tenham passado. A comparação é por SEVERIDADE explícita: antes ela só
        # sobrescrevia `expected`, então `skipped` seguido de `unexpected`
        # mantinha `skipped` e uma falha real virava "não executado".
        anterior = encontrado.get(titulo)
        if anterior is None or _severidade(status) > _severidade(anterior):
            encontrado[titulo] = status
    return encontrado


def montar_evidencias(
    criterios: list[AcceptanceCriterion],
    especificacao: EspecificacaoCriterios,
    titulos_por_criterio: dict[str, str],
    status_dos_testes: dict[str, str],
    recusas: dict[str, str],
    base_url: str,
) -> list[CriterionEvidence]:
    """Traduz o resultado do Playwright para o vocabulário do harness.

    Uma evidência por critério da Task, na ordem da Task — inclusive para os que
    não ganharam teste. Nenhum critério some: a lista precisa cobrir a Task
    inteira para que a nota e a cobertura tenham o mesmo denominador que teriam
    sem QA nenhum.

    Args:
        criterios: Critérios reais da Task (a fonte de verdade da identidade).
        especificacao: O que o QA produziu.
        titulos_por_criterio: Vínculo id → título, de `montar_spec`.
        status_dos_testes: Título → status, de `status_por_titulo`.
        recusas: Id → motivo, para os corpos barrados por `validar_corpo`.
        base_url: URL contra a qual a navegação rodou (entra na evidência).
    """
    nao_verificaveis = {
        item.criterion_id: item.motivo for item in especificacao.nao_verificaveis
    }

    evidencias: list[CriterionEvidence] = []
    for criterio in criterios:
        titulo = titulos_por_criterio.get(criterio.id)
        status = status_dos_testes.get(titulo) if titulo else None

        if status == _STATUS_ATENDIDO:
            outcome = CriterionOutcome.ATENDIDO
            observado = f"O teste de navegação passou contra {base_url}."
        elif status in _STATUS_NAO_ATENDIDO:
            outcome = CriterionOutcome.NAO_ATENDIDO
            observado = (
                f"O teste de navegação falhou contra {base_url} (status "
                f"Playwright: {status})."
            )
        elif titulo is not None:
            # O teste foi gerado mas não produziu resultado: pulado, ou o spec
            # sequer chegou a rodar. Ausência de execução nunca é reprovação.
            outcome = CriterionOutcome.TESTE_NAO_EXECUTADO
            observado = (
                "O teste de navegação foi gerado mas não produziu resultado "
                f"(status Playwright: {status or 'ausente'})."
            )
        elif criterio.id in recusas:
            outcome = CriterionOutcome.SEM_TESTE_MAPEADO
            observado = (
                f"O teste proposto pelo QA foi recusado porque {recusas[criterio.id]}."
            )
        elif criterio.id in nao_verificaveis:
            outcome = CriterionOutcome.NAO_AUTOMATIZAVEL
            observado = (
                "O QA declarou este critério fora do alcance da navegação: "
                f"{nao_verificaveis[criterio.id]}"
            )
        else:
            outcome = (
                CriterionOutcome.SEM_TESTE_MAPEADO
                if criterio.automatable
                else CriterionOutcome.NAO_AUTOMATIZAVEL
            )
            observado = "O QA não propôs teste nem justificativa para este critério."

        evidencias.append(
            CriterionEvidence(
                criterion=criterio.description,
                criterion_id=criterio.id,
                automatable=criterio.automatable,
                outcome=outcome,
                linked_tests=[titulo] if titulo else [],
                check_performed=(
                    f"Teste Playwright contra a aplicação no ar em {base_url}."
                    if titulo
                    else "Nenhum teste de navegação foi executado para este critério."
                ),
                observed=observado,
                checkable=outcome
                in (CriterionOutcome.ATENDIDO, CriterionOutcome.NAO_ATENDIDO),
            )
        )
    return evidencias


def hash_do_spec(conteudo: str) -> str:
    """Impressão do conteúdo do `.spec.ts`, para casá-lo com o seu metadado."""
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def escrever_spec(
    destino: Path,
    task_id: str,
    conteudo: str,
    chave: Optional[str],
    especificacao: EspecificacaoCriterios,
    recusas: dict[str, str],
    titulos: dict[str, str],
) -> Path:
    """Grava o spec e o metadado que permite reusá-lo na rodada seguinte.

    O diretório é imposto pelo runner (`executar_playwright` recusa spec fora
    dele), então não há escolha a fazer aqui — só o nome, que carrega o task_id
    para manter os specs de tasks diferentes distinguíveis na auditoria.

    O `.meta.json` ao lado guarda a CHAVE da situação (código + critérios + URL)
    junto com o que foi decidido a partir dela. Sem esse metadado o reuso seria
    impossível: reexecutar o spec sem saber a que critério cada teste pertence
    não produziria evidência nenhuma.

    Com `chave=None` o spec é gravado mas o metadado é REMOVIDO: a identidade
    da situação não pôde ser estabelecida, então nada aqui é reusável, e deixar
    um metadado velho ao lado de um spec novo é pior que não ter metadado —
    faria a rodada seguinte casar títulos que não existem no arquivo.
    """
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"criterios_{task_id}.spec.ts"
    caminho.write_text(conteudo, encoding="utf-8")

    meta = destino / f"criterios_{task_id}.meta.json"
    if chave is None:
        meta.unlink(missing_ok=True)
        return caminho

    meta.write_text(
        json.dumps(
            {
                "chave": chave,
                # Casa o metadado com o arquivo: se a gravação do spec e a deste
                # metadado divergirem, a rodada seguinte detecta e regenera.
                "hash_spec": hash_do_spec(conteudo),
                "titulos": titulos,
                "recusas": recusas,
                "especificacao": especificacao.model_dump(mode="json"),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return caminho
