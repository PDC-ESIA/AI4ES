"""Camadas de validação anti-alucinação do Agente de Requisitos (Time 1).

A validação acontece em três momentos, do mais forte para o mais fraco:

C1 — `validar_antes_de_salvar` (`before_tool_callback`)
     Roda ANTES de `tool_salvar_artefato_requisito` escrever no disco.
     Devolver um dict faz o ADK pular a execução da tool
     (`flows/llm_flows/functions.py`, Step 3) e entregar esse dict ao LLM
     como resposta da função. Ou seja: o artefato inválido nunca é gravado
     e o modelo recebe os erros a tempo de corrigir no mesmo turno.

C2 — `registrar_artefato_persistido` (`after_tool_callback`)
     Anota em `state["artefatos_persistidos"]` o que foi REALMENTE gravado.
     Essa lista é construída por Python, não pelo LLM, e serve de verdade
     de referência para a auditoria final.

C3 — `auditar_saida_final` (`after_agent_callback`)
     Valida o JSON final contra `AnalystOutput` e o cruza com C2. É a única
     camada capaz de detectar a alucinação mais grave: o agente afirmar no
     resumo que criou um artefato que nunca chegou a criar. Aqui só se
     audita e registra — nesse ponto o agente já terminou e não há como
     pedir correção.

A matriz de rastreabilidade fica fora destas camadas: ela é escrita pelo
próprio LLM e não é auditada aqui.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from .schemas import AnalystOutput, chave_normalizada

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.tools import BaseTool
    from google.adk.tools.tool_context import ToolContext
else:
    CallbackContext = Any  # type: ignore[misc,assignment]
    BaseTool = Any  # type: ignore[misc,assignment]
    ToolContext = Any  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)

TOOL_SALVAR = "tool_salvar_artefato_requisito"
TOOL_DUVIDA = "gerar_doubt_artifact"

# Chave de state onde C2 acumula o que foi gravado e C4 lê.
STATE_ARTEFATOS = "artefatos_persistidos"
STATE_AUDITORIA = "requirements_audit"

# Termos que identificam o glossário como artefato afetado por uma dúvida.
_TERMOS_GLOSSARIO = ("glossario", "glossary")

# ---------------------------------------------------------------------------
# C1 — Validação estrutural do Markdown antes da gravação
# ---------------------------------------------------------------------------

# Rótulo que deve aparecer na linha "Tipo" da tabela de metadados.
# Só estes quatro tipos têm estrutura Markdown fixa. GLOSSARIO tem formato
# próprio e qualquer outro tipo é catch-all: a tool grava em `Outros/`,
# caminho previsto no prompt para a matriz de rastreabilidade e para os UCs.
_ROTULO_TIPO: dict[str, str] = {
    "HU":  "História de Usuário",
    "RF":  "Requisito Funcional",
    "RNF": "Requisito Não Funcional",
    "RN":  "Regra de Negócio",
}

# Seções `##` que cada tipo precisa ter, além de "Metadados".
_SECOES_OBRIGATORIAS: dict[str, tuple[str, ...]] = {
    "HU":  ("História", "Critérios de Aceitação"),
    "RF":  ("Descrição",),
    "RNF": ("Descrição", "Métrica de Verificação"),
    "RN":  ("Regra",),
}

# Seções que o tipo NÃO pode ter. Critério de aceitação é exclusivo de HU.
_SECOES_PROIBIDAS: dict[str, tuple[str, ...]] = {
    "RF":  ("Critérios de Aceitação",),
    "RNF": ("Critérios de Aceitação",),
    "RN":  ("Critérios de Aceitação",),
}

# Corpo mínimo de uma seção para não ser considerada vazia.
_MIN_CORPO_SECAO = 15

_RE_H1 = re.compile(r"^#\s+(?P<id>[A-Z]{1,4}-\d{3})\s*:\s*(?P<titulo>.+?)\s*$", re.MULTILINE)
_RE_H2 = re.compile(r"^##\s+(?P<titulo>.+?)\s*$", re.MULTILINE)
_RE_LINHA_TABELA = re.compile(r"^\|\s*(?P<campo>[^|]+?)\s*\|\s*(?P<valor>[^|]*?)\s*\|\s*$", re.MULTILINE)


def _secoes(conteudo_md: str) -> dict[str, str]:
    """Mapeia título de seção `##` normalizado → corpo da seção."""
    resultado: dict[str, str] = {}
    matches = list(_RE_H2.finditer(conteudo_md))
    for i, match in enumerate(matches):
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(conteudo_md)
        resultado[chave_normalizada(match.group("titulo"))] = conteudo_md[match.end():fim].strip()
    return resultado


def _tabela_metadados(corpo: str) -> dict[str, str]:
    """Extrai a tabela `| Campo | Valor |` como dict normalizado → valor bruto."""
    linhas: dict[str, str] = {}
    for match in _RE_LINHA_TABELA.finditer(corpo):
        campo = match.group("campo").strip()
        valor = match.group("valor").strip()
        # Ignora cabeçalho e linha separadora (|---|---|).
        if set(campo) <= {"-", ":"} or not campo:
            continue
        linhas[chave_normalizada(campo)] = valor
    return linhas


def validar_artefato_markdown(tipo: str, id_req: str, conteudo_md: str) -> list[str]:
    """Valida os argumentos de `tool_salvar_artefato_requisito`.

    Retorna a lista de erros encontrados (vazia quando o artefato é válido).
    Nenhuma verificação depende de I/O — é função pura sobre os argumentos.
    """
    erros: list[str] = []

    tipo_norm = (tipo or "").strip().upper()
    id_norm = (id_req or "").strip()
    md = conteudo_md or ""

    if not md.strip():
        erros.append("conteudo_md está vazio.")
        return erros

    # Tipos sem estrutura canônica (GLOSSARIO e os catch-all de `Outros/`)
    # passam adiante: exigir deles o layout de HU/RF/RNF/RN bloquearia
    # persistências legítimas, como a da matriz de rastreabilidade.
    if tipo_norm not in _ROTULO_TIPO:
        return erros

    # 1. ID coerente com o tipo.
    if not re.fullmatch(rf"{tipo_norm}-\d{{3}}", id_norm):
        erros.append(
            f"id_req '{id_req}' não corresponde ao tipo '{tipo_norm}'. "
            f"O padrão esperado é {tipo_norm}-999 (ex: {tipo_norm}-001)."
        )

    # 2. Título H1 no formato `# <ID>: <Título>`.
    h1 = _RE_H1.search(md)
    if h1 is None:
        erros.append(
            "conteudo_md não começa com o título H1 no formato "
            f"'# {id_norm or '<ID>'}: <Título>'."
        )
    elif h1.group("id") != id_norm:
        erros.append(
            f"o ID do título H1 ('{h1.group('id')}') difere do argumento "
            f"id_req ('{id_norm}'). Os dois devem ser idênticos."
        )

    secoes = _secoes(md)

    # 3. Tabela de metadados com ID e Tipo consistentes.
    if "metadados" not in secoes:
        erros.append("falta a seção '## Metadados' com a tabela | Campo | Valor |.")
    else:
        metadados = _tabela_metadados(secoes["metadados"])
        if "id" not in metadados:
            erros.append("a tabela de '## Metadados' não tem a linha 'ID'.")
        elif metadados["id"] != id_norm:
            erros.append(
                f"a linha 'ID' dos metadados ('{metadados['id']}') difere de "
                f"id_req ('{id_norm}')."
            )

        rotulo_esperado = _ROTULO_TIPO[tipo_norm]
        if "tipo" not in metadados:
            erros.append("a tabela de '## Metadados' não tem a linha 'Tipo'.")
        elif chave_normalizada(metadados["tipo"]) != chave_normalizada(rotulo_esperado):
            erros.append(
                f"a linha 'Tipo' dos metadados é '{metadados['tipo']}', mas para "
                f"{tipo_norm} deve ser '{rotulo_esperado}'."
            )

    # 4. Seções obrigatórias, presentes e preenchidas.
    for titulo in _SECOES_OBRIGATORIAS.get(tipo_norm, ()):
        chave = chave_normalizada(titulo)
        if chave not in secoes:
            erros.append(f"falta a seção obrigatória '## {titulo}' para o tipo {tipo_norm}.")
        elif len(secoes[chave]) < _MIN_CORPO_SECAO:
            erros.append(f"a seção '## {titulo}' está vazia ou curta demais.")

    # 5. Seções proibidas.
    for titulo in _SECOES_PROIBIDAS.get(tipo_norm, ()):
        if chave_normalizada(titulo) in secoes:
            erros.append(
                f"a seção '## {titulo}' não é permitida em {tipo_norm} — "
                "critérios de aceitação pertencem exclusivamente às HUs. Remova a seção."
            )

    return erros


def validar_antes_de_salvar(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, Any] | None:
    """before_tool_callback — barra artefatos malformados antes da gravação.

    Retorna None quando está tudo certo (a tool executa normalmente) ou um
    dict de erro, que o ADK usa como resposta da função sem executá-la.
    """
    if tool.name != TOOL_SALVAR:
        return None

    erros = validar_artefato_markdown(
        tipo=str(args.get("tipo", "")),
        id_req=str(args.get("id_req", "")),
        conteudo_md=str(args.get("conteudo_md", "")),
    )
    if not erros:
        return None

    logger.warning(
        "[VALIDACAO] Artefato %s %s rejeitado: %s",
        args.get("tipo"), args.get("id_req"), "; ".join(erros),
    )
    detalhes = "\n".join(f"- {erro}" for erro in erros)
    return {
        "result": (
            "ERRO DE VALIDAÇÃO — o artefato NÃO foi salvo.\n"
            f"{detalhes}\n"
            "Corrija os pontos acima e chame tool_salvar_artefato_requisito novamente."
        )
    }


def _e_sobre_glossario(id_artefato_afetado: object) -> bool:
    """True quando o artefato afetado pela dúvida é o glossário."""
    if not isinstance(id_artefato_afetado, str):
        return False
    alvo = chave_normalizada(id_artefato_afetado.strip().strip("[]"))
    return any(termo in alvo for termo in _TERMOS_GLOSSARIO)


def rebaixar_duvida_de_glossario(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, Any] | None:
    """before_tool_callback — dúvida sobre glossário não nasce bloqueante.

    O glossário ainda não é produzido de forma confiável, e o prompt já o
    trata como opcional nesta fase. Mas o modelo, ao esbarrar num termo sem
    definição, chama `gerar_doubt_artifact` com `bloqueante=True` — e aí a
    fase inteira trava por causa do artefato menos crítico que ela produz.

    A correção acontece aqui, antes da gravação, e não na leitura do arquivo:
    o Doubt_Artifact nasce marcado como não-bloqueante, de modo que qualquer
    consumidor a jusante — manifesto, HITL, outro Time — leia o mesmo fato.
    Corrigir na leitura exigiria que cada leitor conhecesse a exceção.

    A dúvida continua registrada e visível: o que se remove é só o poder de
    veto sobre a fase. Retorna None sempre — nunca cancela a tool.
    """
    if tool.name != TOOL_DUVIDA:
        return None
    if not args.get("bloqueante"):
        return None
    if not _e_sobre_glossario(args.get("id_artefato_afetado")):
        return None

    # Mutação in-place: o ADK repassa este mesmo dict à tool (functions.py,
    # `function_args` é compartilhado entre o callback e a chamada).
    args["bloqueante"] = False
    logger.info(
        "[VALIDACAO] Dúvida %s sobre o glossário rebaixada para não-bloqueante.",
        args.get("id_duvida"),
    )
    return None


# ---------------------------------------------------------------------------
# C2 — Registro determinístico do que foi gravado
# ---------------------------------------------------------------------------

_RE_SUCESSO = re.compile(r"^SUCESSO:.*?salvo em\s+(?P<path>.+?)\s*$", re.DOTALL)


def registrar_artefato_persistido(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: Any,
) -> None:
    """after_tool_callback — registra em state o artefato efetivamente gravado.

    Retorna None para preservar a resposta original da tool.
    """
    if tool.name != TOOL_SALVAR:
        return None

    texto = (
        tool_response.get("result", "")
        if isinstance(tool_response, dict)
        else str(tool_response)
    )
    match = _RE_SUCESSO.match(str(texto).strip())
    if match is None:
        return None

    tipo = str(args.get("tipo", "")).strip().upper()
    id_req = str(args.get("id_req", "")).strip()
    registro = {"tipo": tipo, "id": id_req, "path": match.group("path")}

    persistidos: list[dict] = list(tool_context.state.get(STATE_ARTEFATOS, []) or [])
    # Regravação do mesmo artefato substitui o registro anterior.
    persistidos = [p for p in persistidos if not (p["tipo"] == tipo and p["id"] == id_req)]
    persistidos.append(registro)
    tool_context.state[STATE_ARTEFATOS] = persistidos
    return None


# ---------------------------------------------------------------------------
# C4 — Auditoria final: JSON declarado × arquivos gravados
# ---------------------------------------------------------------------------

_COLECOES_ESPERADAS: tuple[str, ...] = (
    "user_stories",
    "functional_requirements",
    "non_functional_requirements",
    "business_rules",
)

# Coleção do AnalystOutput → tipo usado por tool_salvar_artefato_requisito.
_COLECAO_TIPO: dict[str, str] = {
    "user_stories": "HU",
    "functional_requirements": "RF",
    "non_functional_requirements": "RNF",
    "business_rules": "RN",
}

# Chaves do relatório preenchidas pelos cruzamentos. Definem tanto a coerência
# quanto o que se loga — manter as duas leituras na mesma tupla evita que uma
# nova verificação entre no relatório e fique de fora de uma delas.
_CHAVES_CRUZAMENTO: tuple[str, ...] = (
    "colecoes_vazias",
    "ids_duplicados",
    "referencias_orfas",
    "declarados_sem_arquivo",
    "arquivos_sem_declaracao",
)

# Status em que `auditar_analise` retorna ANTES dos cruzamentos. Nesses casos as
# listas acima continuam com o valor inicial — vazias porque nada foi examinado,
# e não porque nada foi encontrado. Logá-las junto das demais faria uma rodada
# ilegível parecer uma rodada limpa.
_STATUS_SEM_CRUZAMENTO: tuple[str, ...] = ("sem_saida", "parse_error")


def extrair_bloco_json(texto: str) -> str | None:
    """Extrai o bloco JSON do texto livre produzido pelo agente.

    O agente escreve raciocínio (PASSO 1..N) antes do JSON final. Tenta
    primeiro a cerca ```json e, na ausência dela, testa cada posição de '{'
    com `raw_decode` e devolve o **maior** objeto decodificado.

    Buscar de trás para frente seria mais barato, mas devolveria o último
    objeto ANINHADO (um item de lista, por exemplo) em vez do envelope
    completo — foi exatamente assim que a matriz sumia quando o agente
    respondia sem cerca de código.
    """
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if match:
        return match.group(1).strip()

    decoder = json.JSONDecoder()
    melhor: str | None = None
    for pos in [m.start() for m in re.finditer(r"\{", texto)]:
        try:
            _, fim = decoder.raw_decode(texto, pos)
        except json.JSONDecodeError:
            continue
        candidato = texto[pos:fim]
        if melhor is None or len(candidato) > len(melhor):
            melhor = candidato
    return melhor


def _erros_pydantic(exc: ValidationError) -> list[str]:
    """Converte erros do Pydantic em mensagens curtas de uma linha."""
    mensagens: list[str] = []
    for erro in exc.errors()[:20]:
        caminho = ".".join(str(parte) for parte in erro["loc"])
        mensagens.append(f"{caminho}: {erro['msg']}")
    return mensagens


def _itens(dados: dict, colecao: str) -> list[dict]:
    """Lê uma coleção do JSON bruto tolerando tipos inesperados."""
    valor = dados.get(colecao)
    if not isinstance(valor, list):
        return []
    return [item for item in valor if isinstance(item, dict)]


def _ids_declarados(dados: dict) -> dict[str, str]:
    """Mapeia ID declarado no JSON → tipo de artefato."""
    ids: dict[str, str] = {}
    for colecao, tipo in {**_COLECAO_TIPO, "use_cases": "UC"}.items():
        for item in _itens(dados, colecao):
            identificador = item.get("id")
            if isinstance(identificador, str) and identificador.strip():
                ids[identificador.strip()] = tipo
    return ids


def _referencias_orfas(dados: dict, ids: dict[str, str]) -> list[str]:
    """Detecta rastreabilidade quebrada: alvo inexistente ou de tipo errado.

    Não basta o ID existir. Um `hu_parent` apontando para outro RF cria um
    vínculo de rastreabilidade falso que passaria despercebido por uma
    checagem de mera existência.
    """
    orfas: list[str] = []

    for rf in _itens(dados, "functional_requirements"):
        pai = rf.get("hu_parent")
        if not (isinstance(pai, str) and pai.strip()):
            continue
        pai = pai.strip()
        origem = rf.get("id", "?")
        if pai not in ids:
            orfas.append(f"{origem}.hu_parent aponta para {pai}, que não foi declarado")
        elif ids[pai] != "HU":
            orfas.append(
                f"{origem}.hu_parent aponta para {pai}, que é um {ids[pai]} e não uma HU"
            )

    return orfas


def _ids_duplicados(dados: dict) -> list[str]:
    """Detecta o mesmo ID usado mais de uma vez dentro da mesma coleção."""
    duplicados: list[str] = []
    for colecao in [*_COLECAO_TIPO, "use_cases"]:
        vistos: set[str] = set()
        for item in _itens(dados, colecao):
            identificador = item.get("id")
            if not isinstance(identificador, str):
                continue
            if identificador in vistos:
                duplicados.append(f"{colecao}: ID {identificador} aparece mais de uma vez")
            vistos.add(identificador)
    return duplicados


def auditar_analise(
    raw_output: str,
    persistidos: list[dict],
) -> dict:
    """Audita a saída final do agente contra os artefatos realmente gravados.

    Função pura: recebe o texto bruto do `output_key` e a lista construída
    por C2, e devolve o relatório de auditoria. Nunca levanta exceção.

    A conformidade com `AnalystOutput` e os cruzamentos são independentes:
    um erro de campo isolado não pode cegar a detecção de alucinação, que é
    justamente o que importa aqui.
    """
    relatorio: dict[str, Any] = {
        "schema_status":           "ok",
        "erros_schema":            [],
        "colecoes_vazias":         [],
        "ids_duplicados":          [],
        "referencias_orfas":       [],
        "declarados_sem_arquivo":  [],
        "arquivos_sem_declaracao": [],
        "total_persistido":        len(persistidos),
        "coerente":                False,
    }

    if not raw_output or not raw_output.strip():
        relatorio["schema_status"] = "sem_saida"
        relatorio["erros_schema"] = ["o agente não produziu saída final"]
        return relatorio

    bloco = extrair_bloco_json(raw_output)
    if bloco is None:
        relatorio["schema_status"] = "parse_error"
        relatorio["erros_schema"] = ["nenhum bloco JSON encontrado na saída final"]
        return relatorio

    try:
        dados = json.loads(bloco)
    except json.JSONDecodeError as exc:
        relatorio["schema_status"] = "parse_error"
        relatorio["erros_schema"] = [str(exc)[:300]]
        return relatorio

    if not isinstance(dados, dict):
        relatorio["schema_status"] = "parse_error"
        relatorio["erros_schema"] = ["a saída final não é um objeto JSON"]
        return relatorio

    # Conformidade estrutural com o schema.
    try:
        AnalystOutput.model_validate(dados)
    except ValidationError as exc:
        relatorio["schema_status"] = "validation_error"
        relatorio["erros_schema"] = _erros_pydantic(exc)

    # Cruzamentos — rodam sobre o JSON bruto, mesmo que o schema tenha falhado.
    relatorio["colecoes_vazias"] = [
        colecao for colecao in _COLECOES_ESPERADAS if not _itens(dados, colecao)
    ]

    ids = _ids_declarados(dados)
    relatorio["ids_duplicados"] = _ids_duplicados(dados)
    relatorio["referencias_orfas"] = _referencias_orfas(dados, ids)

    # Cruzamento com o que C2 registrou. Só compara tipos que são persistidos
    # como arquivo individual — UC e Glossário seguem outro caminho.
    tipos_em_arquivo = set(_COLECAO_TIPO.values())
    ids_em_arquivo = {p["id"] for p in persistidos if p.get("tipo") in tipos_em_arquivo}
    ids_em_json = {id_ for id_, tipo in ids.items() if tipo in tipos_em_arquivo}

    relatorio["declarados_sem_arquivo"] = sorted(ids_em_json - ids_em_arquivo)
    relatorio["arquivos_sem_declaracao"] = sorted(ids_em_arquivo - ids_em_json)

    relatorio["coerente"] = relatorio["schema_status"] == "ok" and not any(
        relatorio[chave] for chave in _CHAVES_CRUZAMENTO
    )
    return relatorio


def _nada_examinado(relatorio: dict) -> bool:
    """Indica auditoria que não teve o que auditar.

    São duas formas de esterilidade, e ambas apagariam os achados de uma passada
    boa se o relatório fosse gravado como se fosse resultado:

    - **saída válida e vazia** — valida contra `AnalystOutput`, porque todas as
      coleções têm default, e seria reportada como `schema_status=ok`;
    - **saída ilegível** — os cruzamentos nem chegam a rodar, então
      `colecoes_vazias` fica vazia por não ter sido calculada, e não por estar
      limpa. Foi essa a brecha: a contagem só reconhecia a primeira forma.

    Ter artefato gravado descarta as duas: aí há fato concreto a reportar, e o
    desencontro entre disco e declaração é exatamente o que se quer registrar.
    """
    if relatorio["total_persistido"] != 0:
        return False
    if relatorio["schema_status"] in _STATUS_SEM_CRUZAMENTO:
        return True
    return len(relatorio["colecoes_vazias"]) == len(_COLECOES_ESPERADAS)


def auditar_saida_final(callback_context: CallbackContext) -> None:
    """after_agent_callback — grava o relatório de auditoria em state.

    Retorna None para não sobrescrever a saída do agente. Qualquer falha é
    degradada em log: auditoria nunca derruba o pipeline.
    """
    try:
        state = callback_context.state
        relatorio = auditar_analise(
            raw_output=str(state.get("analysis_result", "") or ""),
            persistidos=list(state.get(STATE_ARTEFATOS, []) or []),
        )

        # O callback dispara a cada invocação do agente. Uma passada final sem
        # artefatos não pode apagar os achados da passada que produziu tudo.
        if _nada_examinado(relatorio):
            # `parse_error` e `sem_saida` já explicam por que nada foi examinado.
            # Trocá-los por `sem_analise` perderia o diagnóstico mais preciso.
            if relatorio["schema_status"] not in _STATUS_SEM_CRUZAMENTO:
                relatorio["schema_status"] = "sem_analise"
                relatorio["erros_schema"] = [
                    "a saída final não declarou nenhum artefato"
                ]
            relatorio["coerente"] = False
            if state.get(STATE_AUDITORIA):
                logger.warning(
                    "[AUDITORIA] passada estéril (schema=%s); preservando "
                    "auditoria anterior",
                    relatorio["schema_status"],
                )
                return None

        state[STATE_AUDITORIA] = relatorio

        if relatorio["coerente"] and relatorio["schema_status"] == "ok":
            logger.info(
                "[AUDITORIA] saída coerente | %d artefato(s) gravado(s)",
                relatorio["total_persistido"],
            )
            return None

        if relatorio["schema_status"] in _STATUS_SEM_CRUZAMENTO:
            logger.warning(
                "[AUDITORIA] saída ilegível | schema=%s | cruzamentos NÃO "
                "executados (nada foi verificado) | %d artefato(s) gravado(s)",
                relatorio["schema_status"],
                relatorio["total_persistido"],
            )
        else:
            logger.warning(
                "[AUDITORIA] incoerências detectadas | schema=%s | "
                "vazias=%s | duplicados=%s | órfãs=%s | "
                "sem arquivo=%s | sem JSON=%s",
                relatorio["schema_status"],
                *(relatorio[chave] for chave in _CHAVES_CRUZAMENTO),
            )
        for erro in relatorio["erros_schema"]:
            logger.warning("[AUDITORIA] schema: %s", erro)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[AUDITORIA] falha ao auditar saída do agente: %s", exc)
    return None
