"""Tradução de um par do CodeRepair para o que o Reviewer consome, e leitura do veredito.

Módulo puro: não importa nada do agente (o pacote `workflow_coding_review`
importa o workflow inteiro e faz o binding do workspace no import), para que
estas funções possam ser testadas sem bootstrap e sem LLM.

Por resposta avaliada, o reviewer recebe o mesmo que recebe no fim do pipeline:

1. **Código no workspace do coder**: o último bloco ``python`` da resposta vira
   `solution.py` — é o arquivo que o reviewer lista e lê —, precedido do
   cabeçalho de imports com que o LiveCodeBench executa as soluções (o mesmo
   ambiente em que os rótulos pos/neg foram gerados).
2. **Mensagem de entrada**: o contrato de task no formato do context_engineer
   (enunciado + contexto do reparo) e o relato do coder (a explicação da
   resposta, sem o código). No pipeline real, ambos chegam ao reviewer pelo
   histórico da conversa.
3. **`task_iteration_summary` sintético**: sem ele, o gate de cobertura
   (`review_tools._persist_review`) força BLOQUEADO em toda revisão. O summary
   satisfaz o gate, mas o resultado da task declara explicitamente que não
   houve execução — o benchmark não informa ao reviewer que os testes passaram.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .dataset import RepairPair

SOLUTION_FILENAME = "solution.py"
TASK_ID = "TASK-001"
CODE_PLACEHOLDER = f"[código da correção gravado em {SOLUTION_FILENAME}]"

# Marcador que o gate de cobertura insere quando sobrepõe o veredito do LLM.
# Se aparecer num run do benchmark, o summary sintético está errado.
GATE_MARKER = "<!-- task-coverage-gate:start -->"

_COMPLEXIDADE = {"easy": "low", "medium": "medium", "hard": "high"}
_LIMITE_TRECHO_FALHA = 1000

_FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)

# Cabeçalho que o LiveCodeBench (origem do CodeJudgeBench) insere antes de
# executar QUALQUER solução, LeetCode ou stdin (lcb_runner/evaluation/
# testing_util.py, `import_string`). Os rótulos pos/neg foram gerados com ele:
# soluções LeetCode usam `List`, `Counter` etc. sem importar. Sem o cabeçalho,
# o Ruff acusa F821 e o reviewer bloqueia como NameError uma resposta que passa
# nos testes. A supressão de F401/F403/F405 evita ruído dos `import *`; com
# eles, nem o Ruff distingue nome indefinido de nome vindo do ambiente — o
# mesmo vale para o ambiente real.
_LCB_IMPORTS = (
    "from string import *\nfrom re import *\nfrom datetime import *\n"
    "from collections import *\nfrom heapq import *\nfrom bisect import *\n"
    "from copy import *\nfrom math import *\nfrom random import *\n"
    "from statistics import *\nfrom itertools import *\nfrom functools import *\n"
    "from operator import *\nfrom io import *\nfrom sys import *\nfrom json import *\n"
    "from builtins import *\nfrom typing import *\nimport string\nimport re\n"
    "import datetime\nimport collections\nimport heapq\nimport bisect\nimport copy\n"
    "import math\nimport random\nimport statistics\nimport itertools\nimport functools\n"
    "import operator\nimport io\nimport sys\nimport json\nsys.setrecursionlimit(50000)\n"
)
HEADER_START = "# --- AMBIENTE DE EXECUÇÃO DA PLATAFORMA (pré-carregado; não faz parte da resposta) ---"
HEADER_END = "# --- FIM DO AMBIENTE — a resposta avaliada começa abaixo ---"
EXECUTION_HEADER = f"# ruff: noqa: F401, F403, F405\n{HEADER_START}\n{_LCB_IMPORTS}{HEADER_END}\n"


def build_solution_file(code: str) -> str:
    """Conteúdo de `solution.py`: o ambiente de execução + o código da resposta."""
    return f"{EXECUTION_HEADER}\n{code}"


# ---------------------------------------------------------------------------
# Resposta → código + relato
# ---------------------------------------------------------------------------


def extract_code(response: str) -> str | None:
    """Último bloco ``python`` da resposta; na falta, o último bloco qualquer.

    Nas respostas com mais de um bloco, o último é a versão final da correção
    (os anteriores são rascunhos ou trechos citados na explicação).
    """
    blocos = _FENCE_RE.findall(response)
    if not blocos:
        return None
    python = [codigo for tag, codigo in blocos if tag.strip().lower() in ("python", "py", "python3")]
    escolhido = (python or [codigo for _, codigo in blocos])[-1]
    return escolhido.strip("\n") + "\n"


def explanation_without_code(response: str) -> str:
    """A resposta com os blocos de código trocados por um marcador."""
    return _FENCE_RE.sub(CODE_PLACEHOLDER, response).strip()


# ---------------------------------------------------------------------------
# Contrato de task + mensagem de entrada
# ---------------------------------------------------------------------------


def _trecho(valor: object) -> str:
    texto = "" if valor is None else str(valor)
    if len(texto) <= _LIMITE_TRECHO_FALHA:
        return texto
    return texto[:_LIMITE_TRECHO_FALHA] + f"\n… [{len(texto) - _LIMITE_TRECHO_FALHA} caracteres omitidos]"


def _descricao_da_falha(pair: RepairPair) -> str:
    meta = pair.wrong_meta or {}
    linhas = [meta.get("error_message") or "Falha não especificada."]
    for chave, rotulo in (("inputs", "Entrada"), ("expected", "Saída esperada"), ("output", "Saída obtida")):
        if meta.get(chave):
            linhas.append(f"{rotulo}:\n{_trecho(meta[chave])}")
    return "\n\n".join(linhas)


def build_task_contract(pair: RepairPair) -> dict:
    """Task no formato do context_engineer (ver context_engineer/prompt.py, Passo 4)."""
    partes = [
        f"Corrigir a solução de um problema de programação ({pair.platform}, "
        f"dificuldade {pair.difficulty}). A solução anterior falhou nos testes; "
        f"a correção deve ser entregue em `{SOLUTION_FILENAME}`.",
        f"## Enunciado\n{pair.question_content.strip()}",
        "## Ambiente de execução\n"
        f"O topo de `{SOLUTION_FILENAME}` traz, entre os marcadores \"AMBIENTE DE "
        "EXECUÇÃO DA PLATAFORMA\" e \"FIM DO AMBIENTE\", os imports que a plataforma "
        "de avaliação carrega antes de executar qualquer solução (inclusive "
        "`from typing import *` e `from collections import *`). Esse trecho não faz "
        "parte da correção: avalie apenas o código abaixo dele, considerando esses "
        "nomes como disponíveis.",
    ]
    if pair.starter_code:
        partes.append(f"## Assinatura esperada\n```python\n{pair.starter_code.strip()}\n```")
    partes.append(f"## Solução anterior (com defeito)\n```python\n{pair.wrong_code.strip()}\n```")
    partes.append(f"## Falha observada\n{_descricao_da_falha(pair)}")

    return {
        "id": TASK_ID,
        "type": "component",
        "complexity": _COMPLEXIDADE.get(pair.difficulty, "medium"),
        "description": "\n\n".join(partes),
        "business_rules": [],
        "acceptance_criteria": [
            {
                "id": "CA-01",
                "description": (
                    "Produzir a saída correta para toda entrada válida descrita no "
                    "enunciado, respeitando as restrições informadas"
                ),
                "automatable": True,
            },
            {
                "id": "CA-02",
                "description": "Eliminar a falha observada na solução anterior",
                "automatable": True,
            },
        ],
        "contract": {
            "inputs": [],
            "outputs": [SOLUTION_FILENAME],
            "interfaces": [pair.starter_code.strip()] if pair.starter_code else [],
        },
        "requirement_id": "RF-001",
        "requirement_refs": [],
    }


def build_tasks_envelope(pair: RepairPair) -> dict:
    """Envelope completo publicado pelo context_engineer em `state['tasks']`."""
    return {
        "status": "concluido",
        "macro_context": {
            "summary": "Corrigir a solução de um problema de programação competitiva.",
            "product_type": "cli" if not pair.starter_code else "library",
            "tech_stack": ["python"],
            "global_rules": ["Usar somente a biblioteca padrão do Python"],
        },
        "tasks": [build_task_contract(pair)],
    }


def build_reviewer_message(pair: RepairPair, response: str, *, include_explanation: bool = True) -> str:
    """Mensagem de entrada do reviewer para uma das respostas do par.

    O texto é o mesmo para `pos` e `neg` e para todos os modelos — só muda o
    relato do coder, que é parte da resposta avaliada (protocolo §7).
    """
    envelope = json.dumps(build_tasks_envelope(pair), ensure_ascii=False, indent=2)
    partes = [
        "# CONTEXTO DO PIPELINE",
        "O context_engineer publicou a task abaixo e o coder entregou a correção "
        f"em `{SOLUTION_FILENAME}`, no workspace do coder. Faça a revisão final.",
        f"## Tasks publicadas pelo context_engineer\n```json\n{envelope}\n```",
    ]
    if include_explanation:
        partes.append(f"## Relato do coder\n{explanation_without_code(response)}")
    return "\n\n".join(partes)


def synthetic_iteration_summary() -> dict:
    """`task_iteration_summary` mínimo e válido para o gate de cobertura.

    As listas de ids satisfazem `review_tools.cobertura_comprovada`. O resultado
    da task NÃO alega aprovação pelo executor: o reviewer lê
    `status=nao_executado; término=benchmark_sem_execucao`.
    """
    return {
        "input_valid": True,
        "input_errors": [],
        "expected_task_ids": [TASK_ID],
        "processed_task_ids": [TASK_ID],
        "approved_task_ids": [TASK_ID],
        "accepted_task_ids": [],
        "task_results": {
            TASK_ID: {
                "status": "nao_executado",
                "conceito": None,
                "nota_final": None,
                "motivo_terminacao": "benchmark_sem_execucao",
            }
        },
        "cobertura_completa": True,
        "qualidade_completa": True,
    }


# ---------------------------------------------------------------------------
# Leitura do markdown do reviewer
# ---------------------------------------------------------------------------

_STATUS_LENIENTE_RE = re.compile(r"status\W{0,6}(aprovado|bloqueado)", re.IGNORECASE)
_TITULO_RE = re.compile(r"^#{1,6}\s+(.*)$")
_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_ARQUIVO_RE = re.compile(r"`?([\w./-]+\.py)`?")
_SEVERIDADES = (
    ("critical", re.compile(r"critical|cr[ií]tic", re.IGNORECASE)),
    ("warning", re.compile(r"warning|aviso|alerta", re.IGNORECASE)),
    ("info", re.compile(r"\binfo\b|informativ", re.IGNORECASE)),
)
_CAMADAS = ("completude", "arquitetura", "corretude", "testes")


@dataclass
class ParsedReview:
    """Leitura tolerante do markdown do reviewer — diagnóstico, não veredito.

    O veredito oficial é o do manifesto (busca exata de "Status: APROVADO" /
    "Status: BLOQUEADO"). Esta leitura existe para explicar os casos em que o
    manifesto não reconhece nada: se `lenient_status` acha um status que o
    manifesto não achou, o problema é de formato, não de julgamento.
    """

    lenient_status: str | None
    status_mentions: list[str] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    gate_applied: bool = False


_SEVERIDADE_EXPLICITA_RE = re.compile(
    r"(?:severity|severidade)\W{0,6}(critical|cr[ií]tic[ao]?|warning|aviso|info)", re.IGNORECASE
)
_CAMADA_EXPLICITA_RE = re.compile(
    r"(?:camada|layer)\W{0,6}(completude|arquitetura|corretude|testes)", re.IGNORECASE
)
_CAMADA_QUALQUER_RE = re.compile(r"completude|arquitetura|corretude|testes", re.IGNORECASE)
_NENHUM_RE = re.compile(
    r"(?:nenhum|nenhuma)(?:\s+(?:problema|issue|item|ponto)\S*.*)?\.?|n/a|-", re.IGNORECASE
)


def _severidade(texto: str) -> str:
    for nome, padrao in _SEVERIDADES:
        if padrao.search(texto):
            return nome
    return "unknown"


def _severidade_do_item(primeira_linha: str, texto: str, severidade_secao: str | None) -> str:
    """Rótulo explícito ("Severity: critical") > primeira linha > subtítulo > texto todo."""
    explicita = _SEVERIDADE_EXPLICITA_RE.search(texto)
    if explicita:
        return _severidade(explicita.group(1))
    for candidata in (_severidade(primeira_linha), severidade_secao, _severidade(texto)):
        if candidata and candidata != "unknown":
            return candidata
    return "unknown"


def _camada(texto: str) -> str:
    """Rótulo explícito ("Camada: corretude") > primeira camada citada no texto."""
    explicita = _CAMADA_EXPLICITA_RE.search(texto)
    if explicita:
        return explicita.group(1).lower()
    qualquer = _CAMADA_QUALQUER_RE.search(texto)
    return qualquer.group(0).lower() if qualquer else "unknown"


def _itens_da_secao(markdown: str) -> list[tuple[list[str], str | None]]:
    """Agrupa a seção "Issues" em itens: a linha do item + suas continuações.

    O reviewer escreve a mesma issue de vários jeitos: tudo numa linha, ou o
    item seguido de linhas como "File: solution.py — Camada: corretude" e de
    sub-itens ("  - Descrição: ..."). Só um marcador de lista no recuo do
    primeiro item abre uma issue nova; o resto (linhas recuadas, sub-itens,
    blocos de código) pertence ao item corrente.
    """
    itens: list[tuple[list[str], str | None]] = []
    dentro = em_codigo = False
    severidade_secao: str | None = None
    recuo_base: int | None = None
    for linha in markdown.splitlines():
        if linha.lstrip().startswith("```"):
            em_codigo = not em_codigo
            if dentro and itens:
                itens[-1][0].append(linha)
            continue
        if not em_codigo:
            titulo = _TITULO_RE.match(linha)
            if titulo:
                texto_titulo = titulo.group(1).strip()
                if re.match(r"issues?\b", texto_titulo, re.IGNORECASE):
                    dentro, severidade_secao, recuo_base = True, None, None
                elif dentro and linha.startswith("## "):
                    dentro = False
                elif dentro:
                    sev = _severidade(texto_titulo)
                    severidade_secao = sev if sev != "unknown" else severidade_secao
                continue
        if not dentro or not linha.strip():
            continue
        item = None if em_codigo else _ITEM_RE.match(linha)
        recuo = len(linha) - len(linha.lstrip())
        if item and (recuo_base is None or recuo <= recuo_base):
            recuo_base = recuo if recuo_base is None else recuo_base
            itens.append(([item.group(1).strip()], severidade_secao))
        elif itens:
            itens[-1][0].append(linha.strip())
    return itens


def _parse_issues(markdown: str) -> list[dict]:
    """Issues da seção "Issues": severidade, camada e arquivo de cada item."""
    issues: list[dict] = []
    for linhas, severidade_secao in _itens_da_secao(markdown):
        primeira = linhas[0]
        if not primeira or _NENHUM_RE.fullmatch(primeira):
            continue
        texto = " ".join(linhas)
        arquivo = _ARQUIVO_RE.search(texto)
        issues.append(
            {
                "severity": _severidade_do_item(primeira, texto, severidade_secao),
                "description": texto,
                "file": arquivo.group(1) if arquivo else None,
                "layer": _camada(texto),
            }
        )
    return issues


def parse_review_markdown(markdown: str) -> ParsedReview:
    """Extrai status (tolerante) e issues do markdown produzido pelo reviewer."""
    mencoes = [m.upper() for m in _STATUS_LENIENTE_RE.findall(markdown or "")]
    distintos = sorted(set(mencoes))
    if len(distintos) == 1:
        leniente = distintos[0]
    elif len(distintos) > 1:
        leniente = "AMBIGUO"
    else:
        leniente = None
    return ParsedReview(
        lenient_status=leniente,
        status_mentions=mencoes,
        issues=_parse_issues(markdown or ""),
        gate_applied=GATE_MARKER in (markdown or ""),
    )
