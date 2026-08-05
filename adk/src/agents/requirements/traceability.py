"""Construção determinística da Matriz de Rastreabilidade — Requisitos (Time 1).

Motivação: a matriz é obrigatória pelo prompt, mas desaparecia com frequência.
Dez dos doze campos de `TraceabilityMatrixItem` são função determinística dos
artefatos já produzidos — inclusive `lacuna_detectada`, que é uma operação de
conjunto. Pedir ao LLM que transcreva uma tabela de 10 colunas × N linhas é
trabalho de escriturário: caro, sem julgamento e sistematicamente abandonado no
fim da geração.

Aqui o LLM só entrega `traceability_rationale` (`origem` e `motivo_inclusao`,
que dependem do texto de entrada). Todo o resto é montado em código, no mesmo
padrão determinístico de `manifest.emit_requirements_manifest`: zero LLM, falha
degradada em log, nunca derruba o pipeline.
"""

import json
import logging
from typing import TYPE_CHECKING, Any

from shared.workspace import get_agent_workspace

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
else:
    CallbackContext = Any  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)

STATE_MATRIZ = "traceability_matrix"
ID_MATRIZ = "MTR-001"
SUBPASTA_MATRIZ = "Outros"

_NAO_IDENTIFICADO = "Não identificado"
_SEM_DERIVADOS = "Nenhum"
_CASOS_TESTE = "A definir"
_AGENTE_ORIGEM = "requirements_agent"

# Coleção do AnalystOutput → tipo de artefato na matriz. A ordem define a
# ordem das linhas da tabela.
_COLECOES: tuple[tuple[str, str], ...] = (
    ("user_stories", "HU"),
    ("functional_requirements", "RF"),
    ("use_cases", "UC"),
    ("non_functional_requirements", "RNF"),
    ("business_rules", "RN"),
)

# Tipos que precisam de origem declarada (rastreabilidade backward).
_EXIGEM_BACKWARD = frozenset({"RF", "UC", "RNF", "RN"})

_COLUNAS = (
    "ID do Artefato",
    "Tipo",
    "Descrição/Título",
    "Origem",
    "Motivo de Inclusão",
    "Prioridade",
    "Rastreabilidade Backward",
    "Rastreabilidade Forward",
    "Critérios de Aceitação",
    "Caso(s) de Teste",
)


def _itens(dados: dict, colecao: str) -> list[dict]:
    """Lê uma coleção do JSON bruto tolerando tipos inesperados."""
    valor = dados.get(colecao)
    if not isinstance(valor, list):
        return []
    return [item for item in valor if isinstance(item, dict)]


def _texto(valor: object, padrao: str = _NAO_IDENTIFICADO) -> str:
    """Normaliza um campo textual vindo do JSON do LLM."""
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return padrao


def _descricao(item: dict) -> str:
    """RN não tem `title`; os demais tipos têm."""
    return _texto(item.get("title") or item.get("description"), "Sem descrição")


def _rationale(dados: dict) -> dict[str, dict]:
    """Indexa por ID o julgamento fornecido pelo LLM."""
    indice: dict[str, dict] = {}
    for entrada in _itens(dados, "traceability_rationale"):
        identificador = _texto(entrada.get("id_artefato"), "")
        if identificador:
            indice[identificador] = entrada
    return indice


def _coletar_artefatos(dados: dict) -> list[dict]:
    """Achata as coleções do AnalystOutput numa lista ordenada de artefatos."""
    artefatos: list[dict] = []
    for colecao, tipo in _COLECOES:
        for item in _itens(dados, colecao):
            identificador = _texto(item.get("id"), "")
            if not identificador:
                continue
            artefatos.append({
                "id": identificador,
                "tipo": tipo,
                "descricao": _descricao(item),
                "prioridade": _texto(item.get("priority")),
                "criterios": [
                    c for c in item.get("acceptance_criteria", []) or []
                    if isinstance(c, str) and c.strip()
                ],
                "hu_parent": _texto(item.get("hu_parent"), ""),
            })
    return artefatos


def _vinculos(artefatos: list[dict]) -> tuple[dict[str, list], dict[str, list]]:
    """Deriva backward e forward a partir de `hu_parent`.

    Um vínculo só é criado quando o alvo existe E é uma HU: `hu_parent`
    apontando para outro RF é dado sujo, e materializá-lo na matriz
    transformaria o erro do LLM em rastreabilidade aparentemente legítima.
    """
    tipos = {a["id"]: a["tipo"] for a in artefatos}
    backward: dict[str, list] = {}
    forward: dict[str, list] = {}

    for artefato in artefatos:
        pai = artefato["hu_parent"]
        if not pai or tipos.get(pai) != "HU":
            continue
        backward.setdefault(artefato["id"], []).append({
            "id_artefato_relacionado": pai,
            "tipo_artefato_relacionado": "HU",
            "tipo_relacao": "deriva_de",
        })
        forward.setdefault(pai, []).append({
            "id_artefato_relacionado": artefato["id"],
            "tipo_artefato_relacionado": artefato["tipo"],
            "tipo_relacao": "origina",
        })
    return backward, forward


def _lacuna(artefato: dict, backward: list, forward: list) -> str | None:
    """Aplica as regras de lacuna do prompt. Retorna a descrição ou None."""
    tipo = artefato["tipo"]
    if tipo in _EXIGEM_BACKWARD and not backward:
        return f"{artefato['id']} não possui artefato de origem (backward ausente)"
    if tipo == "HU" and not forward:
        return f"{artefato['id']} não originou nenhum RF ou UC (forward ausente)"
    return None


def _celula(valores: list[dict], vazio: str) -> str:
    """Renderiza uma lista de links como célula da tabela Markdown."""
    if not valores:
        return vazio
    return ", ".join(link["id_artefato_relacionado"] for link in valores)


def renderizar_markdown(matriz: dict) -> str:
    """Renderiza a matriz como tabela Markdown com as 10 colunas obrigatórias."""
    linhas = [
        f"# {matriz['id']}: Matriz de Rastreabilidade",
        "",
        "| " + " | ".join(_COLUNAS) + " |",
        "|" + "|".join(["---"] * len(_COLUNAS)) + "|",
    ]

    for item in matriz["itens"]:
        criterios = ", ".join(item["criterios_aceitacao"]) or "Não aplicável"
        linhas.append("| " + " | ".join([
            item["id_artefato"],
            item["tipo"],
            item["descricao"],
            item["origem"],
            item["motivo_inclusao"],
            item["prioridade"],
            _celula(item["rastreabilidade_backward"], _NAO_IDENTIFICADO),
            _celula(item["rastreabilidade_forward"], _SEM_DERIVADOS),
            criterios,
            item["casos_teste"],
        ]) + " |")

    if matriz["lacunas_candidatas_doubt"]:
        linhas += ["", "## Lacunas de Rastreabilidade Detectadas", ""]
        linhas += [f"- {lacuna}" for lacuna in matriz["lacunas_candidatas_doubt"]]

    return "\n".join(linhas) + "\n"


def construir_matriz(dados: dict) -> dict | None:
    """Monta a matriz a partir do JSON do agente. Função pura.

    Devolve None quando a rodada não declarou nenhum artefato — não há matriz
    de coisa nenhuma, e forjar uma vazia só criaria ruído.
    """
    artefatos = _coletar_artefatos(dados)
    if not artefatos:
        return None

    julgamento = _rationale(dados)
    backward, forward = _vinculos(artefatos)

    itens: list[dict] = []
    lacunas: list[str] = []

    for artefato in artefatos:
        identificador = artefato["id"]
        links_backward = backward.get(identificador, [])
        links_forward = forward.get(identificador, [])
        entrada = julgamento.get(identificador, {})

        lacuna = _lacuna(artefato, links_backward, links_forward)
        if lacuna:
            lacunas.append(lacuna)

        itens.append({
            "id_artefato": identificador,
            "tipo": artefato["tipo"],
            "descricao": artefato["descricao"],
            "origem": _texto(entrada.get("origem")),
            "motivo_inclusao": _texto(entrada.get("motivo_inclusao")),
            "prioridade": artefato["prioridade"],
            "rastreabilidade_backward": links_backward,
            "rastreabilidade_forward": links_forward,
            "criterios_aceitacao": artefato["criterios"],
            "casos_teste": _CASOS_TESTE,
            "id_agente_origem": _AGENTE_ORIGEM,
            "lacuna_detectada": lacuna is not None,
            "lacuna_descricao": lacuna,
        })

    matriz = {
        "id": ID_MATRIZ,
        "itens": itens,
        "lacunas_candidatas_doubt": lacunas,
        "markdown": "",
    }
    matriz["markdown"] = renderizar_markdown(matriz)
    return matriz


def gerar_matriz_rastreabilidade(callback_context: CallbackContext) -> None:
    """after_agent_callback — constrói, persiste e publica a matriz.

    Roda ANTES de `validation.auditar_saida_final`, que injeta o resultado no
    JSON do agente antes de validar contra `AnalystOutput`. Retorna None para
    não sobrescrever a saída do agente.
    """
    # Import tardio: `validation` importa deste módulo apenas constantes, e o
    # inverso criaria ciclo em tempo de import.
    from .validation import extrair_bloco_json

    try:
        state = callback_context.state
        bruto = str(state.get("analysis_result", "") or "")
        bloco = extrair_bloco_json(bruto)
        if bloco is None:
            logger.warning("[MATRIZ] saída sem bloco JSON; matriz não construída")
            return None

        dados = json.loads(bloco)
        if not isinstance(dados, dict):
            logger.warning("[MATRIZ] saída final não é um objeto JSON")
            return None

        matriz = construir_matriz(dados)
        if matriz is None:
            logger.warning("[MATRIZ] nenhum artefato declarado; matriz não construída")
            return None

        state[STATE_MATRIZ] = matriz

        destino = get_agent_workspace("requirements_agent") / SUBPASTA_MATRIZ
        destino.mkdir(parents=True, exist_ok=True)
        (destino / f"{ID_MATRIZ}.md").write_text(matriz["markdown"], encoding="utf-8")

        logger.info(
            "[MATRIZ] %s construída | %d item(ns) | %d lacuna(s)",
            ID_MATRIZ, len(matriz["itens"]), len(matriz["lacunas_candidatas_doubt"]),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MATRIZ] Falha ao construir matriz de rastreabilidade: %s", exc)
    return None
