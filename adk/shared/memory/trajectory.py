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

## O que a run de SUCESSO precisa carregar (corrigido em 14/08)

Uma primeira versão desta montagem só trazia objetivo, veredito e **os estágios
que falharam**. Numa run aprovada esse último bloco vira literalmente *"Nenhum —
todos os estágios passaram"*, e o destilador recebia cinco linhas sem conteúdo:
nada do que foi construído, nada do caminho até a correção. O resultado medido
em 13/08 foram lições de sucesso vazias — *"trabalhar em ciclos curtos até
convergir"* —, em que o modelo se agarrava ao único fato quantitativo
disponível, a contagem de iterações.

Daí os dois blocos acrescentados aqui:

- **a entrega** (`montar_manifesto`) — os arquivos produzidos e o `run.json`;
- **as tentativas anteriores** (`resumir_tentativas` sobre `carregar_historico`)
  — o que quebrou em cada passagem do loop antes da que passou. É o insumo mais
  instrutivo que uma run convergente tem, e era o que se perdia inteiro.
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

# Tentativas anteriores: só o resumo do que falhou, nunca a evidência bruta —
# essa já está no report da tentativa corrente quando é ela que falha. Oito
# tentativas cobrem folgadamente o teto de iterações do loop (default 5).
_MAX_TENTATIVAS = 8
_MAX_SUMMARY_TENTATIVA = 300

_MAX_ARQUIVOS_MANIFESTO = 60

# Subpasta em `coder/execution/` com uma cópia do report por iteração. Escrita
# por `harness_execucao._arquivar_report_da_iteracao`; o nome é compartilhado.
_HISTORICO_DIRNAME = "historico"

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


def carregar_historico(report_path: Optional[str]) -> list[dict]:
    """Carrega os reports arquivados das iterações desta run, em ordem.

    O harness grava `<task_id>.report.json` **sem a iteração no nome**, então
    cada passagem do loop sobrescreve a anterior: no fim de uma run aprovada só
    resta o report que passou, com zero estágios em falha. A cópia por iteração
    vive em `historico/`, ao lado dele.

    A pasta é desta run por construção — está dentro do `workspace_output/`, que
    `init_workspace()` apaga a cada fresh run. O filtro por `task_id` isola a
    task quando a run produz mais de uma.

    Devolve `[]` em qualquer falha: sem histórico a trajetória fica mais pobre,
    nunca quebrada.
    """
    if not report_path:
        return []

    try:
        alvo = Path(report_path)
        task_id = alvo.name.split(".", 1)[0]
        pasta = alvo.parent / _HISTORICO_DIRNAME
        if not task_id or not pasta.is_dir():
            return []

        reports: list[dict] = []
        for arquivo in sorted(pasta.glob(f"{task_id}.*.report.json")):
            try:
                reports.append(json.loads(arquivo.read_text(encoding="utf-8")))
            except Exception:
                continue  # um arquivo ilegível não invalida os outros
        return reports
    except Exception:
        return []


def resumir_tentativas(historico: list[dict], report_atual: dict) -> str:
    """Uma linha por tentativa anterior desta run: o que falhou e com que código.

    É o insumo que faltava à trajetória de **sucesso**. Uma run que passou na 4ª
    iteração só tem lição a dar se disser o que quebrou nas três primeiras.

    A tentativa corrente sai da lista — os blocos seguintes já a trazem com
    evidência bruta. A comparação é por `generated_at`, e não por posição: se o
    arquivamento da corrente tiver falhado, nada é descartado por engano.
    """
    if not historico:
        return ""

    atual_em = str(report_atual.get("generated_at") or "")
    anteriores = [
        r
        for r in historico
        if not atual_em or str(r.get("generated_at") or "") != atual_em
    ][:_MAX_TENTATIVAS]

    if not anteriores:
        return ""

    linhas = []
    for r in anteriores:
        falhos = [
            s for s in r.get("stages", []) if s.get("status") in _STATUS_COM_EVIDENCIA
        ][:_MAX_ESTAGIOS]
        if falhos:
            detalhe = "; ".join(
                f"`{s.get('stage')}` ({s.get('error_code') or 'sem código'}): "
                f"{_truncar(s.get('summary', ''), _MAX_SUMMARY_TENTATIVA)}"
                for s in falhos
            )
        else:
            detalhe = "nenhum estágio falhou"
        linhas.append(
            f"- iteração {r.get('iteration', '?')} — "
            f"{r.get('overall_status', 'desconhecido')}: {detalhe}"
        )

    return "\n".join(linhas)


def montar_manifesto(src_dir) -> str:
    """Lista o que a run entregou, mais o conteúdo do `run.json` se existir.

    Numa run aprovada é o único conteúdo concreto que a trajetória tem — sem
    isto o destilador de sucesso não vê nada do que foi construído.

    Só caminhos e o manifesto de execução: o código em si estouraria o contexto
    e não é o que gera lição generalizável.
    """
    try:
        raiz = Path(src_dir)
        if not raiz.is_dir():
            return ""
        arquivos = sorted(
            p.relative_to(raiz).as_posix()
            for p in raiz.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        )
    except Exception:
        return ""

    if not arquivos:
        return ""

    linhas = [f"- {a}" for a in arquivos[:_MAX_ARQUIVOS_MANIFESTO]]
    if len(arquivos) > _MAX_ARQUIVOS_MANIFESTO:
        linhas.append(f"- … e mais {len(arquivos) - _MAX_ARQUIVOS_MANIFESTO} arquivo(s)")

    bloco = "\n".join(linhas)

    run_json = raiz / "run.json"
    if run_json.is_file():
        try:
            bloco += "\n\nManifesto `run.json`:\n" + _truncar(
                run_json.read_text(encoding="utf-8")
            )
        except Exception:
            pass  # o manifesto é bônus; a lista de arquivos já vale

    return bloco


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
    historico: Optional[list[dict]] = None,
    manifesto: str = "",
) -> str:
    """Formata a evidência da run como o texto de entrada da destilação.

    A ordem é deliberada — objetivo, veredito, entrega, caminho percorrido,
    evidência bruta — para que o modelo leia o *que se queria*, o *que a máquina
    decidiu*, o *que foi construído*, o *que se tentou antes*, e só então o
    material bruto. Assim ele ancora a lição no veredito determinístico em vez
    de reinterpretar logs livremente.

    `historico` e `manifesto` são o que dá conteúdo à trajetória de sucesso —
    ver o cabeçalho do módulo. Ambos são opcionais: ausentes, a montagem degrada
    para a forma anterior em vez de falhar.
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

    if manifesto:
        partes.append("# O que esta run entregou\n" + manifesto)

    tentativas = resumir_tentativas(historico or [], report)
    if tentativas:
        partes.append(
            "# Tentativas anteriores nesta run\n"
            "O caminho até o resultado acima. Cada linha é uma passagem pelo loop "
            "coder⇄executor que NÃO passou; o que as separa do resultado final é "
            "exatamente o que se aprendeu.\n" + tentativas
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
