"""Renderização do `report.md` a partir do relatório consolidado (`report.json`)."""

from __future__ import annotations

from typing import Any

from .metrics import classificar_parada


def _pct(valor: float | None) -> str:
    return "—" if valor is None else f"{valor * 100:.1f}%"


def _taxa(bloco: dict[str, Any]) -> str:
    if not bloco or not bloco.get("n"):
        return "— (n = 0)"
    ic = bloco.get("ic95")
    intervalo = f" — IC 95%: [{_pct(ic[0])}, {_pct(ic[1])}]" if ic else ""
    return f"{bloco['k']}/{bloco['n']} ({_pct(bloco['taxa'])}){intervalo}"


def _linha_correcao(correcao: dict[str, Any] | None) -> list[str]:
    if not correcao:
        return ["- **Correção oficial:** não executada neste relatório."]
    codigo = correcao.get("returncode")
    linhas = [f"- **Correção oficial:** código de saída `{codigo}`"]
    if codigo not in (0, None):
        linhas.append(
            f"\n> **ATENÇÃO:** o harness oficial terminou com código {codigo}. "
            "Confira `grading/run_evaluation.log` antes de usar estes números."
        )
    return linhas


def _cabecalho(relatorio: dict[str, Any]) -> list[str]:
    params = relatorio.get("parametros", {})
    ambiente = relatorio.get("ambiente", {})
    dataset = relatorio.get("dataset", {})
    return [
        "# Benchmark SWE-bench Verified — loop coder → executor",
        "",
        f"- **Gerado em:** {relatorio.get('generated_at')}",
        f"- **Modelo:** `{params.get('model')}`",
        f"- **Instâncias:** {relatorio['metricas']['n_instancias']} "
        f"(seed {params.get('seed')}, limit {params.get('limit')})",
        f"- **Dataset:** `{dataset.get('repo_id')}` @ `{str(dataset.get('revision'))[:12]}`",
        f"- **Harness oficial:** swebench {ambiente.get('swebench_version') or '—'}",
        f"- **Teto do loop (`max_iterations`):** {ambiente.get('max_loop_iterations')}",
        f"- **Commit do repositório:** `{str(ambiente.get('git_commit'))[:12]}`"
        + (" (árvore com alterações locais)" if ambiente.get("git_dirty") else ""),
        *_linha_correcao(relatorio.get("correcao")),
        "",
        "> Linha de base com amostra pequena: leia sempre o intervalo de confiança "
        "junto da taxa. Limitações na seção final e no README.",
        "",
    ]


def _secao_metrica_1(m1: dict[str, Any]) -> list[str]:
    linhas = [
        "## Métrica 1 — Taxa de resolução (harness oficial)",
        "",
        f"- **Resolvidas:** {_taxa(m1)}",
    ]
    excluidas = m1.get("excluidas_gold") or []
    if excluidas:
        linhas += [
            f"- **Sem as {len(excluidas)} instância(s) que nem o patch oficial resolve** "
            f"(`--gold-sanity`): {_taxa(m1.get('sem_exclusoes_gold', {}))}",
            f"- **Excluídas pelo gold:** {', '.join(excluidas)}",
        ]
    linhas += [
        "",
        "| Status no SWE-bench | Instâncias |",
        "| ------------------- | ---------- |",
    ]
    linhas += [f"| {status} | {n} |" for status, n in m1.get("por_status", {}).items()]
    causas = m1.get("causas_nao_resolvidas") or {}
    if causas:
        linhas += ["", "Causas registradas entre as não resolvidas: "
                   + ", ".join(f"{c}: {n}" for c, n in causas.items()) + "."]
    return linhas + [""]


def _secao_metrica_2(m2: dict[str, Any]) -> list[str]:
    rodadas = m2.get("rodadas", {})
    linhas = [
        "## Métrica 2 — Rodadas do loop e motivo de parada",
        "",
        f"- **Rodadas por instância:** média {rodadas.get('media')}, mediana "
        f"{rodadas.get('mediana')}, mín. {rodadas.get('min')}, máx. {rodadas.get('max')}",
        "",
        "| Rodadas | Instâncias |",
        "| ------- | ---------- |",
    ]
    linhas += [f"| {r} | {n} |" for r, n in rodadas.get("distribuicao", {}).items()]
    linhas += [
        "",
        "| Motivo de parada | Instâncias | Detalhe (`motivo_terminacao`) |",
        "| ---------------- | ---------- | ----------------------------- |",
    ]
    detalhes = m2.get("motivo_parada_detalhe", {})
    for categoria, n in m2.get("motivo_parada", {}).items():
        detalhe = ", ".join(f"{d}: {c}" for d, c in detalhes.get(categoria, {}).items())
        linhas.append(f"| {categoria} | {n} | {detalhe} |")
    divergencias = m2.get("divergencias_rodadas_vs_historico") or []
    if divergencias:
        linhas += [
            "",
            f"> {len(divergencias)} instância(s) com rodadas ≠ tamanho do histórico de "
            "notas (rodada sem veredito gravado): " + ", ".join(divergencias),
        ]
    return linhas + [""]


def _secao_metrica_3(m3: dict[str, Any]) -> list[str]:
    matriz = m3.get("matriz", {})
    linhas = [
        "## Métrica 3 — Concordância do validador",
        "",
        f"Instâncias com gabarito conhecido: {m3.get('com_gabarito')} "
        f"(fora da matriz: {m3.get('sem_gabarito')}, das quais "
        f"{m3.get('excluidas_gold', 0)} excluídas pelo `--gold-sanity`).",
        "",
        "| | Resolvida (SWE-bench) | Não resolvida |",
        "| --- | --- | --- |",
        f"| **Validador aprovou** | {matriz.get('vp', 0)} | {matriz.get('fp', 0)} (falso positivo) |",
        f"| **Validador não aprovou** | {matriz.get('fn', 0)} (falso negativo) | {matriz.get('vn', 0)} |",
        "",
        f"- **Falsos positivos entre as aprovações:** {_taxa(m3.get('taxa_fp_entre_aprovadas', {}))}",
        f"- **Precisão do validador:** {_taxa(m3.get('precisao', {}))}",
        f"- **Recall do validador:** {_taxa(m3.get('recall', {}))}",
    ]
    if m3.get("falsos_positivos_ids"):
        linhas.append("- **Instâncias com falso positivo:** " + ", ".join(m3["falsos_positivos_ids"]))
    ressalvas = m3.get("aceito_com_ressalvas", {})
    linhas += [
        f"- **Aceitas com ressalvas pelo sistema** (validador reprovou, política "
        f"aceitou): {ressalvas.get('total', 0)}, das quais {ressalvas.get('resolvidas', 0)} "
        "resolvidas",
        "",
        "O validador aprova pelo status técnico da suíte que o PRÓPRIO coder declarou. "
        "Os qualificadores mostram o que sustentava cada aprovação:",
        "",
        "| Qualificador | Aprovações | Entre os falsos positivos |",
        "| ------------ | ---------- | ------------------------- |",
    ]
    qualif = m3.get("aprovacoes_qualificadas", {})
    qualif_fp = m3.get("falsos_positivos_qualificados", {})
    for nome in ("suite_vazia_ou_pulada", "patch_vazio", "testes_nao_identificados"):
        linhas.append(f"| {nome} | {qualif.get(nome, 0)} | {qualif_fp.get(nome, 0)} |")
    return linhas + [""]


def _secao_sanidade_executor(sanidade: dict[str, Any] | None) -> list[str]:
    if not sanidade:
        return []
    linhas = [
        "## Ambiente do executor com a solução oficial (`--executor-sanity`)",
        "",
        f"Com o patch e os testes oficiais aplicados, o harness do executor deu sucesso "
        f"em **{sanidade.get('sucesso')}/{sanidade.get('n')}** instâncias — é o teto de "
        "aprovações corretas que o validador consegue dar neste ambiente.",
        "",
        "| Resultado | Instâncias |",
        "| --------- | ---------- |",
    ]
    linhas += [f"| {r} | {n} |" for r, n in (sanidade.get("por_resultado") or {}).items()]
    return linhas + [""]


def _secao_por_repo(por_repo: dict[str, Any]) -> list[str]:
    linhas = [
        "## Por repositório",
        "",
        "| Repositório | Instâncias | Resolvidas | Aprovadas pelo validador |",
        "| ----------- | ---------- | ---------- | ------------------------ |",
    ]
    linhas += [
        f"| {repo} | {v['n']} | {v['resolvidas']} | {v['aprovadas']} |"
        for repo, v in por_repo.items()
    ]
    return linhas + [""]


def _secao_operacional(op: dict[str, Any]) -> list[str]:
    uso = op.get("uso_llm", {})

    def _lista(chave: str) -> str:
        ids = op.get(chave) or []
        return f"{len(ids)}" + (f" ({', '.join(ids)})" if ids else "")

    return [
        "## Operacional",
        "",
        f"- **Erros operacionais:** {_lista('erros_operacionais')}",
        f"- **Timeouts de instância:** {_lista('timeouts')}",
        f"- **Ambiente restaurado pela guarda:** {_lista('ambiente_violado')}",
        f"- **Coder usou virtualenv no `run.json`:** {_lista('venv_no_manifesto')}",
        f"- **Duração total do loop:** {op.get('duracao_total_s', 0)}s",
        f"- **Interações com LLM:** {uso.get('llm_interactions', 0)}",
        f"- **Tokens (entrada/saída/total):** {uso.get('prompt_tokens', 0)}/"
        f"{uso.get('completion_tokens', 0)}/{uso.get('total_tokens', 0)}",
        *(
            f"  - `{agente}`: {linha.get('llm_interactions', 0)} interações, "
            f"{linha.get('prompt_tokens', 0)}/{linha.get('completion_tokens', 0)} tokens"
            for agente, linha in (uso.get("por_agente") or {}).items()
        ),
        "",
    ]


def _secao_instancias(relatorio: dict[str, Any]) -> list[str]:
    teto = relatorio["metricas"]["metrica_2_loop"].get("teto_max_iterations")
    linhas = [
        "## Por instância",
        "",
        "| Instância | Rodadas | Parada | Validador | SWE-bench | Arquivos no patch |",
        "| --------- | ------- | ------ | --------- | --------- | ----------------- |",
    ]
    for r in relatorio.get("instancias", []):
        categoria, detalhe = classificar_parada(
            r.get("motivo_terminacao"), int(r.get("rodadas") or 0), teto
        )
        patch = r.get("patch") or {}
        arquivos = "vazio" if patch.get("vazio") else str(len(patch.get("arquivos") or []))
        grading = (r.get("grading") or {}).get("status", "not_graded")
        linhas.append(
            f"| {r['instance_id']} | {r.get('rodadas')} | {categoria} ({detalhe}) | "
            f"{r.get('veredito_validador') or '—'} | {grading} | {arquivos} |"
        )
    return linhas + [""]


def _secao_leitura() -> list[str]:
    return [
        "## Como ler estes números",
        "",
        "- **Amostra pequena:** com 30 instâncias, cada uma vale 3,3 pontos "
        "percentuais; compare runs pelo intervalo de confiança, não pela taxa pontual.",
        "- **Métrica 1 mede o loop inteiro:** depende mais do coder (sem ferramenta "
        "de busca, lendo arquivos inteiros) do que do executor.",
        "- **Métrica 3 mede o sinal de parada:** um falso positivo significa que a "
        "suíte do coder passou e o bug continuou — testes fracos ou ausentes, ou um "
        "validador permissivo. Os qualificadores ajudam a separar os casos.",
        "- **O gabarito também erra:** os testes oficiais só cobrem o que o PR "
        "original testou. Revise à mão as discordâncias da métrica 3.",
        "",
    ]


def render_markdown(relatorio: dict[str, Any]) -> str:
    """Resumo legível do run, com as três métricas da issue #417."""
    metricas = relatorio["metricas"]
    linhas = _cabecalho(relatorio)
    linhas += _secao_metrica_1(metricas["metrica_1_resolucao"])
    linhas += _secao_metrica_2(metricas["metrica_2_loop"])
    linhas += _secao_metrica_3(metricas["metrica_3_validador"])
    linhas += _secao_sanidade_executor(relatorio.get("sanidade_executor"))
    linhas += _secao_por_repo(metricas["por_repositorio"])
    linhas += _secao_operacional(metricas["operacional"])
    linhas += _secao_instancias(relatorio)
    linhas += _secao_leitura()
    return "\n".join(linhas)
