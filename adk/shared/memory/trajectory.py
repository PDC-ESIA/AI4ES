"""Montagem da trajetória entregue ao destilador.

O `induce_memory.py` do ReasoningBank monta a trajetória parseando o log textual
do mini-swe-agent (`load_blocks`, `extract_think_and_action`) — um formato que
não existe aqui. Nossa entrada é melhor: em vez de reconstituir o que aconteceu
a partir de prosa, lemos o `ExecutionReport` que o harness já produziu, com
estágio, status, `error_code` e evidência bruta.

Duas decisões de recorte:

- **Estágios `pulado` ficam de fora.** São consequência em cascata do que falhou
  antes ("Abortado: ..."), não trazem informação. É o mesmo critério que o
  `montar_error_report` do executor já aplica (`_STATUS_COM_EVIDENCIA`).
- **A evidência bruta é truncada por campo.** Um `runtime_logs_tail` pode ter
  dezenas de KB; sem teto, a trajetória estoura o contexto e a destilação falha
  justamente nas runs mais interessantes, que são as que produziram mais log.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

# Truncagem por campo de evidência. Generoso o bastante para caber um traceback
# inteiro (que é o que costuma carregar a causa raiz) e pequeno o bastante para
# vários estágios somados ainda caberem no contexto.
_MAX_EVIDENCIA_CHARS = 2000
_MAX_ESTAGIOS = 6

_STATUS_COM_EVIDENCIA = ("falha", "erro")


def normalizar_status(bruto) -> str:
    """Reduz um status de veredito à sua forma canônica em minúsculas.

    Existe por causa de uma assimetria real do ADK, encontrada num run de
    13/08: **o estado vivo da sessão guarda o `Enum`, o `session.db` guarda a
    string**. `ValidationVerdict.status` é um `VerdictStatus(str, Enum)`, então
    dentro da run `state['validation']['status']` é o objeto — e
    `str(VerdictStatus.APROVADO)` devolve `'VerdictStatus.APROVADO'`, não
    `'aprovado'`. Só ao serializar para o banco vira `'aprovado'`.

    Comparar sem normalizar fazia uma run **aprovada** ser destilada como
    falha, com o prompt errado do ReasoningBank, e o LLM chegava a citar
    `VerdictStatus.APROVADO` no texto da lição.

    Aceita as três formas: o enum, `'VerdictStatus.APROVADO'` e `'aprovado'`.
    """
    if bruto is None:
        return ""
    valor = getattr(bruto, "value", bruto)  # Enum → .value; str → ele mesmo
    texto = str(valor).strip()
    if "." in texto:  # 'VerdictStatus.APROVADO' → 'APROVADO'
        texto = texto.rsplit(".", 1)[-1]
    return texto.casefold()


def carregar_report(report_path: Optional[str]) -> dict:
    """Lê o ExecutionReport do disco. Devolve {} em qualquer falha."""
    if not report_path:
        return {}
    try:
        return json.loads(Path(report_path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def error_codes_do_report(report: dict) -> list[str]:
    """Extrai os `error_code` dos estágios que falharam, preservando a ordem.

    É a chave de recuperação determinística da próxima run — ver
    `retrieve._pre_filtrar`.
    """
    codigos: list[str] = []
    for estagio in report.get("stages", []):
        codigo = estagio.get("error_code")
        if codigo and codigo not in codigos:
            codigos.append(codigo)
    return codigos


def _truncar(valor, limite: int = _MAX_EVIDENCIA_CHARS) -> str:
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)
    if len(texto) <= limite:
        return texto
    return texto[:limite] + f"\n… [truncado, {len(texto) - limite} caracteres omitidos]"


def montar_trajetoria(
    report: dict,
    validation: Optional[dict] = None,
    *,
    tech_stack: str = "",
    objetivo: str = "",
) -> str:
    """Formata a evidência da run como o texto de entrada da destilação.

    A ordem é deliberada — objetivo, veredito, estágios em falha, evidência —
    para que o modelo leia o *que se queria*, depois o *que a máquina decidiu*,
    e só então o material bruto. Assim ele ancora a lição no veredito
    determinístico em vez de reinterpretar logs livremente.
    """
    partes: list[str] = []

    if objetivo:
        partes.append(f"# Objetivo da task\n{objetivo}")

    if tech_stack:
        partes.append(f"# Stack\n{tech_stack}")

    if validation:
        # Normalizado para o modelo nunca ver 'VerdictStatus.APROVADO' — ver
        # `normalizar_status`. Vazar o repr do Enum já contaminou lições reais.
        partes.append(
            "# Veredito determinístico do validador\n"
            f"status: {normalizar_status(validation.get('status')) or 'desconhecido'}\n"
            f"motivo do bloqueio: {validation.get('blocking_reason') or 'n/a'}"
        )
        nao_atendidos = [
            cv
            for cv in validation.get("criteria_verdicts", [])
            if normalizar_status(cv.get("status")) != "atendido"
        ]
        if nao_atendidos:
            linhas = [
                f"- [{normalizar_status(cv.get('status'))}] "
                f"{cv.get('criterion')}: {cv.get('reasoning')}"
                for cv in nao_atendidos
            ]
            partes.append("# Critérios não atendidos\n" + "\n".join(linhas))

    partes.append(
        "# Resultado global da execução\n"
        f"{report.get('overall_status', 'desconhecido')} "
        f"(iteração {report.get('iteration', 'n/a')})"
    )

    falhos = [
        s for s in report.get("stages", []) if s.get("status") in _STATUS_COM_EVIDENCIA
    ][:_MAX_ESTAGIOS]

    if falhos:
        blocos = []
        for estagio in falhos:
            cabecalho = (
                f"## Estágio `{estagio.get('stage')}` — "
                f"status={estagio.get('status')} "
                f"error_code={estagio.get('error_code') or 'n/a'}"
            )
            corpo = [cabecalho, estagio.get("summary", "")]
            for chave, valor in (estagio.get("evidence") or {}).items():
                corpo.append(f"### evidência: {chave}\n{_truncar(valor)}")
            blocos.append("\n".join(c for c in corpo if c))
        partes.append("# Estágios que falharam, com evidência bruta\n" + "\n\n".join(blocos))
    else:
        partes.append("# Estágios que falharam\nNenhum — todos os estágios passaram.")

    return "\n\n".join(partes)
