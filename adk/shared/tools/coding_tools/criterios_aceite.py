"""Critério de aceite com identidade estável — entrada do fluxo de codificação.

Um critério de aceite deixa de ser uma frase solta e passa a ser um objeto com
`id` próprio e uma classificação de automatizabilidade. Duas coisas a jusante
dependem disso:

- **Identidade**: o mapa que liga teste ↔ critério — e, com ele, toda evidência
  determinística de atendimento — precisa de uma chave estável. Casar por
  igualdade de TEXTO é frágil: qualquer reescrita do critério, em qualquer ponto
  do fluxo, quebra o vínculo em silêncio.
- **Automatizabilidade**: decidida UMA vez, por quem escreve o critério, porque
  é propriedade da FRASE ("dá para comprovar isto com teste automatizado?") e
  não do que aconteceu na execução. Perguntar de novo a cada rodada custaria uma
  chamada de LLM por rodada e, pior, poderia responder diferente entre rodadas
  para o mesmo critério — o que tornaria instável qualquer decisão tomada em
  cima da resposta.

O QUE `automatable` SIGNIFICA, exatamente: "comprovável pelas capacidades de
teste que este fluxo tem HOJE" — e não "automatizável em termos absolutos". A
distinção é deliberada e tem consequência prática.

Um critério de jornada de interface ("consigo criar um Ensaio pela interface
web") é automatizável em tese, com um navegador dirigido por código. Classificá-
lo como `True` por causa disso faria o fluxo cobrar do coder um teste que ele
não tem como escrever com as ferramentas de que dispõe — gastando rodada atrás
de rodada em algo impossível, que é precisamente a patologia que este desenho
existe para não repetir. Sob a leitura "capacidade atual", ele é `False`: entra
na medição como não coberto, sem nunca ser cobrado.

Consequência para quem evoluir o fluxo: ao adicionar uma capacidade de teste
nova (E2E de navegador, por exemplo), a fronteira do que é automatizável se
move, e quem precisa ser atualizado é o PROMPT de quem escreve os critérios
(`context_engineer/prompt.py`) — não este módulo. Tasks antigas seguem com a
classificação da época; como elas são efêmeras (vivem no workspace de uma
execução), não há migração a fazer.

NÃO confundir `automatable` com `CriterionEvidence.checkable` (ver
`harness_schemas.py`). São perguntas diferentes:

  - `automatable`: o critério PODE ser coberto por teste automatizado? Fixo,
    decidido na autoria da task, igual em toda rodada.
  - `checkable`: o harness CONSEGUIU comprovar o critério NAQUELA execução?
    Varia a cada rodada (a aplicação pode nem ter subido).

`normalizar_criterios` é o único ponto de entrada, e é TOTAL: nunca levanta
exceção. Isso é deliberado e segue o mesmo princípio documentado em
`TasksOutput` (ver `context_engineer/schemas.py`) — a lista vem de um LLM, e uma
resposta malformada não pode derrubar a invocação inteira. Item inaproveitável é
descartado com aviso no log; o resto segue.

A normalização precisa existir aqui, e não só no schema do `context_engineer`,
porque a task chega ao harness pelo DISCO: `tool_salvar_task_cr` grava o JSON
cru produzido pelo LLM, sem passar pelo modelo Pydantic. Quem lê esse arquivo
recebe exatamente o que o modelo escreveu — inclusive o formato antigo, uma
lista de strings.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Formato do id de critério, escopado à task (CA-01, CA-02...). O reconhecimento
# é tolerante (`CA-1`, `ca-007`) mas a saída é sempre CANÔNICA, com no mínimo
# dois dígitos: o id atravessa o fluxo escrito por um LLM em um ponto (a task) e
# lido por outro LLM em outro (o mapa teste ↔ critério do manifesto). Se as duas
# pontas puderem grafar o MESMO critério de formas diferentes — `CA-1` na task,
# `CA-01` no manifesto, porque o exemplo do prompt usa dois dígitos — o vínculo
# quebra em silêncio, que é exatamente o que o id existe para evitar.
#
# Canonizar pode fazer dois ids distintos na origem colapsarem no mesmo
# (`CA-1` + `CA-01`): isso é tratado como id repetido pelo 2º passe de
# `normalizar_criterios`, que realoca o segundo para o próximo livre.
_ID_RE = re.compile(r"^CA-(\d+)$")

# Dígitos mínimos do id canônico. Números maiores não são truncados: CA-100
# permanece CA-100.
_DIGITOS_ID = 2

# Chaves aceitas para o texto do critério, em ordem de preferência. `criterion`
# entra como alias porque é o nome usado em `CriterionEvidence`.
_CHAVES_TEXTO = ("description", "criterion")

# Chaves aceitas para a automatizabilidade. O alias em português existe pelo
# mesmo motivo de `Contract._coerce_interfaces`: o prompt é em português e o
# modelo às vezes traduz a chave.
_CHAVES_AUTOMATABLE = ("automatable", "automatizavel")

# Default quando a classificação vem ausente ou ilegível.
#
# Assume-se AUTOMATIZÁVEL de propósito, e a assimetria dos custos é a razão:
# um falso `True` custa, no máximo, uma cobrança de teste que o coder não tem
# como atender — e essa cobrança é limitada por desenho. Um falso `False` é pior
# e silencioso: o critério nunca é cobrado, nunca ganha teste, e some da
# cobertura sem que ninguém perceba que ele PODERIA ter sido comprovado.
_AUTOMATABLE_PADRAO = True


class AcceptanceCriterion(BaseModel):
    """Um critério de aceite identificado e classificado."""

    id: str = Field(
        description="Identificador do critério dentro da task (ex.: CA-01)"
    )
    description: str = Field(
        description="Texto do critério de aceite, como escrito pelo autor da task"
    )
    automatable: bool = Field(
        default=_AUTOMATABLE_PADRAO,
        description=(
            "Se o critério pode ser comprovado por teste automatizado COM AS "
            "CAPACIDADES ATUAIS do fluxo (ver a docstring do módulo). False "
            "para critérios subjetivos ou de jornada de interface, que exigem "
            "instrumentação que o fluxo ainda não tem (ex.: 'visual "
            "minimalista', 'consigo ver a página final do álbum')."
        ),
    )


def _texto_do_dict(dados: dict) -> str:
    """Primeiro valor textual não vazio entre as chaves aceitas."""
    for chave in _CHAVES_TEXTO:
        valor = dados.get(chave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    return ""


def _formatar_id(numero: int) -> str:
    """O id canônico de um número de ordem (1 → CA-01; 100 → CA-100)."""
    return f"CA-{numero:0{_DIGITOS_ID}d}"


def canonizar_id(bruto: Any) -> Optional[str]:
    """O id já canonizado; None quando não é reconhecível como id de critério.

    Reconhece variações de grafia (`ca-1`, ` CA-007 `) e devolve sempre a forma
    canônica, para que as duas pontas do mapa teste ↔ critério grafem o mesmo
    critério do mesmo jeito. É a ÚNICA definição da gramática do id no fluxo:
    quem precisar interpretar um id (a task, o manifesto) passa por aqui.
    """
    if not isinstance(bruto, str):
        return None
    casado = _ID_RE.match(bruto.strip().upper())
    return _formatar_id(int(casado.group(1))) if casado else None


def _automatable_do_dict(dados: dict) -> bool:
    """Lê a automatizabilidade declarada, caindo para o padrão se ilegível.

    Aceita string ("true"/"false") além de booleano: a saída do LLM é JSON, mas
    nada garante que o valor não venha citado.
    """
    for chave in _CHAVES_AUTOMATABLE:
        if chave not in dados:
            continue
        valor = dados[chave]
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, str) and valor.strip().casefold() in ("true", "false"):
            return valor.strip().casefold() == "true"
        logger.warning(
            "Critério de aceite com %s=%r ilegível; assumindo %s.",
            chave,
            valor,
            _AUTOMATABLE_PADRAO,
        )
        break
    return _AUTOMATABLE_PADRAO


def _extrair(item: Any) -> Optional[tuple[Optional[str], str, bool]]:
    """Reduz um item da lista a `(id_proposto, description, automatable)`.

    Returns:
        None quando o item não carrega critério aproveitável — o que inclui o
        formato antigo com string vazia e qualquer tipo inesperado.
    """
    if isinstance(item, AcceptanceCriterion):
        return canonizar_id(item.id), item.description, item.automatable

    # Formato antigo: lista de strings, sem id nem classificação.
    if isinstance(item, str):
        texto = item.strip()
        return (None, texto, _AUTOMATABLE_PADRAO) if texto else None

    if isinstance(item, dict):
        texto = _texto_do_dict(item)
        if not texto:
            logger.warning("Critério de aceite sem texto foi descartado: %r", item)
            return None
        return canonizar_id(item.get("id")), texto, _automatable_do_dict(item)

    logger.warning(
        "Critério de aceite de tipo inesperado (%s) foi descartado.",
        type(item).__name__,
    )
    return None


def normalizar_criterios(valor: Any) -> list[AcceptanceCriterion]:
    """Converte qualquer forma aceita de `acceptance_criteria` na canônica.

    Aceita a lista antiga de strings, a nova lista de dicts/modelos, e qualquer
    mistura das duas — o formato antigo continua chegando pelo disco enquanto
    tasks geradas antes desta mudança ainda existirem no workspace.

    Ids válidos declarados pelo autor são preservados; os demais itens (sem id,
    com id fora do formato, ou com id repetido) recebem o próximo `CA-NN` livre.
    Preservar o id declarado importa porque é ele que o mapa teste ↔ critério
    referencia: reatribuir um id válido quebraria esse vínculo silenciosamente.

    Args:
        valor: O conteúdo bruto de `acceptance_criteria`, vindo do state ou do
            JSON da task em disco.

    Returns:
        Critérios normalizados, com ids únicos dentro da lista. Lista vazia
        quando não há nada aproveitável — nunca levanta.
    """
    if not isinstance(valor, list):
        if valor is not None:
            logger.warning(
                "acceptance_criteria é %s; esperado list. Nenhum critério "
                "reconhecido.",
                type(valor).__name__,
            )
        return []

    brutos = [extraido for item in valor if (extraido := _extrair(item)) is not None]

    # 1º passe: reserva os ids declarados válidos, na ordem de aparição. A
    # PRIMEIRA ocorrência de um id fica com ele; repetições caem no 2º passe —
    # inclusive as criadas pela canonização (`CA-1` e `CA-01` viram o mesmo id).
    reservados: set[str] = set()
    ids: list[Optional[str]] = []
    for id_proposto, _, _ in brutos:
        if id_proposto is not None and id_proposto not in reservados:
            reservados.add(id_proposto)
            ids.append(id_proposto)
        else:
            ids.append(None)

    # 2º passe: preenche o que sobrou com o próximo CA-NN ainda não reservado.
    contador = 0
    for indice, id_final in enumerate(ids):
        if id_final is not None:
            continue
        while True:
            contador += 1
            candidato = _formatar_id(contador)
            if candidato not in reservados:
                break
        reservados.add(candidato)
        ids[indice] = candidato

    return [
        AcceptanceCriterion(
            id=id_final,
            description=descricao,
            automatable=automatable,
        )
        for id_final, (_, descricao, automatable) in zip(ids, brutos)
    ]


def descricoes(criterios: list[AcceptanceCriterion]) -> list[str]:
    """Só os textos, para os contratos a jusante que ainda esperam `list[str]`."""
    return [criterio.description for criterio in criterios]


# ---------------------------------------------------------------------------
# Mapa teste ↔ critério — o vínculo declarado pelo coder no `run.json`
# ---------------------------------------------------------------------------


class MapaDeTestes(BaseModel):
    """O mapa do manifesto, já casado com os critérios reais da Task.

    Separar `por_criterio` de `ids_desconhecidos` é o que permite tratar as duas
    situações como coisas diferentes: a primeira é cobertura declarada, a
    segunda é um erro de anotação do coder — que precisa ser VISÍVEL (senão o
    critério aparece como descoberto e ninguém entende por quê), mas nunca
    tratado como falha de execução.
    """

    por_criterio: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Id canônico do critério → identificadores dos testes que o cobrem. "
            "Só contém ids que existem de fato na Task."
        ),
    )
    ids_desconhecidos: list[str] = Field(
        default_factory=list,
        description=(
            "Chaves do manifesto descartadas, como o coder as escreveu: id fora "
            "da gramática (`CRIT-1`) ou que não corresponde a critério algum "
            "desta Task (`CA-09` numa task com 3 critérios)."
        ),
    )


def normalizar_mapa_de_testes(
    bruto: Any, criterios: list[AcceptanceCriterion]
) -> MapaDeTestes:
    """Casa o mapa declarado no `run.json` com os critérios reais da Task.

    Duas coisas acontecem aqui, e ambas dependem de conhecer os dois lados — por
    isso não vivem no modelo do manifesto, que não conhece a Task:

    1. **Canonização das chaves**: o coder escreve o mapa lendo a Task, mas
       nada garante que ele reproduza a grafia exata do id. `canonizar_id`
       resolve `CA-1` ↔ `CA-01` antes do casamento, que é a razão de a
       canonização existir (ver `_ID_RE`).
    2. **Casamento com a Task**: uma chave que não corresponde a nenhum critério
       é descartada e registrada. Ela não pode virar cobertura — apontaria
       testes para um critério inexistente — nem pode falhar a execução: é erro
       de anotação, não defeito do artefato.

    Args:
        bruto: `RunManifest.acceptance_tests` (já com a forma garantida) ou
            qualquer coisa, se vier de outra origem.
        criterios: Os critérios da Task, já normalizados.

    Returns:
        `MapaDeTestes` com o vínculo utilizável e o refugo separado. Nunca
        levanta: as duas pontas são escritas por LLM.
    """
    conhecidos = {criterio.id for criterio in criterios}
    por_criterio: dict[str, list[str]] = {}
    desconhecidos: list[str] = []

    if not isinstance(bruto, dict):
        if bruto is not None:
            logger.warning(
                "Mapa teste↔critério é %s; esperado dict. Nenhum vínculo "
                "considerado.",
                type(bruto).__name__,
            )
        return MapaDeTestes()

    for chave, testes in bruto.items():
        id_canonico = canonizar_id(chave)
        if id_canonico is None or id_canonico not in conhecidos:
            desconhecidos.append(str(chave))
            continue
        testes_validos = [t for t in testes if isinstance(t, str) and t.strip()]
        if not testes_validos:
            continue
        # Um id repetido em grafias diferentes (`CA-1` e `CA-01`) converge para a
        # mesma chave: as listas se somam em vez de uma sobrescrever a outra.
        acumulado = por_criterio.setdefault(id_canonico, [])
        acumulado.extend(t for t in testes_validos if t not in acumulado)

    if desconhecidos:
        logger.warning(
            "Mapa teste↔critério cita %d id(s) que não existem na Task: %s. "
            "Os critérios correspondentes seguem sem cobertura declarada.",
            len(desconhecidos),
            ", ".join(desconhecidos),
        )

    return MapaDeTestes(por_criterio=por_criterio, ids_desconhecidos=desconhecidos)
