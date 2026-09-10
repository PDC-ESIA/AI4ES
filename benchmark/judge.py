"""LLM-as-a-Judge: avalia as execuções coletadas segundo a rubrica do protocolo.

Para cada execução em benchmark/runs/, consolida os artefatos num único texto
anonimizado e submete a rubrica de 8 critérios aos juízes definidos em config.py
(sempre modelos distintos do que produziu a resposta).

É idempotente: julgamentos já gravados são pulados, então o comando pode ser
reexecutado à vontade depois de uma queda no meio da campanha.

Uso:
    adk/.venv/bin/python benchmark/judge.py
    adk/.venv/bin/python benchmark/judge.py --modelo gpt-5-mini --caso RE-07
    adk/.venv/bin/python benchmark/judge.py --dry-run
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "adk"))

import litellm  # noqa: E402

from config import (  # noqa: E402
    CANDIDATOS,
    CRITERIOS,
    EXCLUIR_AUTOAVALIACAO,
    JUDGMENTS,
    MAX_TENTATIVAS_JSON,
    ORDEM_PASTAS,
    ROTULOS,
    RUNS,
    TEMPERATURA_JUIZ,
    TIMEOUT_S,
    intersecao,
    juizes_de,
    modelo_litellm,
)
from shared.llm import copilot_completion_kwargs  # noqa: E402

_ESCALA = (
    "1 = Muito inadequado | 2 = Insatisfatório | 3 = Adequado | "
    "4 = Bom | 5 = Excelente"
)

# Identificadores de fornecedor/modelo são removidos do texto antes do envio.
# Protocolo §14: o juiz não deve receber informação sobre quem produziu a resposta.
# O sufixo de versão/variante é consumido junto — "Gemini 3.8 Flash" inteiro vira
# [MODELO], senão o número da versão continuaria identificando a autoria.
_MARCAS = re.compile(
    r"\b(?:gemini|gpt|chatgpt|claude|sonnet|opus|haiku|openai|anthropic|copilot|"
    r"llama|mistral|deepseek|grok|qwen)"
    r"(?:[\s\-._]*(?:\d[\w.]*|flash|pro|mini|lite|nano|turbo|preview|instruct|"
    r"codex|sonnet|opus|haiku))*",
    re.IGNORECASE,
)


def _esquema_json() -> str:
    campos = ",\n".join(
        f'  "{c}": {{"nota": <inteiro de 1 a 5>, "justificativa": "<texto>"}}'
        for c in CRITERIOS
    )
    return (
        "{\n"
        + campos
        + ',\n  "pontos_fortes": ["<texto>", ...],'
        + '\n  "oportunidades_melhoria": ["<texto>", ...]\n}'
    )


def prompt_juiz(resposta: str) -> list[dict]:
    criterios = "\n".join(f"* {ROTULOS[c]} (`{c}`)" for c in CRITERIOS)
    sistema = (
        "Você é um especialista em Engenharia de Requisitos e conhece as boas "
        "práticas descritas na norma ISO/IEC/IEEE 29148.\n\n"
        "Avalie a resposta produzida para a tarefa apresentada. Considere "
        "exclusivamente a qualidade técnica da resposta. Você não sabe qual "
        "modelo a produziu e não deve especular a respeito.\n\n"
        f"Avalie os seguintes critérios:\n{criterios}\n\n"
        f"Para cada critério atribua uma nota inteira de 1 a 5 ({_ESCALA}) e "
        "justifique a nota.\n\n"
        "Responda EXCLUSIVAMENTE com um objeto JSON válido, sem cercas de "
        "código e sem qualquer texto fora do JSON, exatamente neste formato:\n\n"
        f"{_esquema_json()}"
    )
    usuario = (
        "Abaixo estão os artefatos de requisitos produzidos para o caso. "
        "Avalie-os como uma entrega única.\n\n"
        "<artefatos>\n"
        f"{resposta}\n"
        "</artefatos>"
    )
    return [
        {"role": "system", "content": sistema},
        {"role": "user", "content": usuario},
    ]


def montar_resposta(run_dir: Path) -> tuple[str, int]:
    """Concatena os artefatos em ordem canônica e remove marcas de autoria."""
    base = run_dir / "artifacts"

    def chave(p: Path) -> tuple[int, str]:
        pasta = p.parent.name
        prio = ORDEM_PASTAS.index(pasta) if pasta in ORDEM_PASTAS else len(ORDEM_PASTAS)
        return (prio, p.name)

    blocos = []
    for md in sorted(base.rglob("*.md"), key=chave):
        corpo = md.read_text(encoding="utf-8").strip()
        blocos.append(f"### {md.relative_to(base)}\n\n{corpo}")

    texto = "\n\n---\n\n".join(blocos)
    anonimo, n = _MARCAS.subn("[MODELO]", texto)
    return anonimo, n


def extrair_json(bruto: str) -> dict:
    texto = bruto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", texto).strip()
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ValueError("resposta do juiz não contém objeto JSON")
    return json.loads(texto[inicio : fim + 1])


def validar(avaliacao: dict) -> dict[str, int]:
    notas = {}
    for c in CRITERIOS:
        item = avaliacao.get(c)
        if not isinstance(item, dict) or "nota" not in item:
            raise ValueError(f"critério ausente ou malformado: {c}")
        nota = int(item["nota"])
        if not 1 <= nota <= 5:
            raise ValueError(f"nota fora da escala 1-5 em {c}: {nota}")
        notas[c] = nota
    return notas


def avaliar(resposta: str, juiz: str) -> dict:
    modelo = modelo_litellm(juiz)
    mensagens = prompt_juiz(resposta)
    extras = copilot_completion_kwargs(modelo)
    erros = []

    for tentativa in range(1, MAX_TENTATIVAS_JSON + 1):
        inicio = time.monotonic()
        resp = litellm.completion(
            model=modelo,
            messages=mensagens,
            temperature=TEMPERATURA_JUIZ,
            timeout=TIMEOUT_S,
            **extras,
        )
        latencia = time.monotonic() - inicio
        bruto = resp.choices[0].message.content or ""
        try:
            avaliacao = extrair_json(bruto)
            notas = validar(avaliacao)
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            erros.append(f"tentativa {tentativa}: {exc}")
            continue

        uso = getattr(resp, "usage", None)
        return {
            "juiz": juiz,
            "notas": notas,
            "nota_final": round(sum(notas.values()) / len(notas), 4),
            "justificativas": {
                c: avaliacao[c].get("justificativa", "") for c in CRITERIOS
            },
            "pontos_fortes": avaliacao.get("pontos_fortes", []),
            "oportunidades_melhoria": avaliacao.get("oportunidades_melhoria", []),
            "latencia_s": round(latencia, 3),
            "tokens_prompt": getattr(uso, "prompt_tokens", None),
            "tokens_resposta": getattr(uso, "completion_tokens", None),
            "tokens_total": getattr(uso, "total_tokens", None),
            "tentativas": tentativa,
        }

    raise RuntimeError(
        f"juiz {juiz} não devolveu JSON válido em {MAX_TENTATIVAS_JSON} tentativas: "
        + " | ".join(erros)
    )


def listar_execucoes(modelo: str | None, caso: str | None) -> list[Path]:
    execucoes = []
    for m in CANDIDATOS:
        if modelo and m != modelo:
            continue
        raiz = RUNS / m
        if not raiz.is_dir():
            continue
        for run_dir in sorted(raiz.glob("*/exec-*")):
            if caso and run_dir.parent.name != caso:
                continue
            if (run_dir / "artifacts").is_dir():
                execucoes.append(run_dir)
    return execucoes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", choices=CANDIDATOS, help="filtra por candidato")
    parser.add_argument("--caso", help="filtra por caso")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="lista o que seria julgado, sem chamar nenhum modelo",
    )
    args = parser.parse_args()

    JUDGMENTS.mkdir(parents=True, exist_ok=True)
    execucoes = listar_execucoes(args.modelo, args.caso)
    if not execucoes:
        sys.exit("nenhuma execução encontrada em benchmark/runs/")

    sobrepostos = intersecao()
    if sobrepostos:
        if EXCLUIR_AUTOAVALIACAO:
            print(
                "aviso: "
                + ", ".join(sobrepostos)
                + " atuam como candidato e juiz; a autoavaliação é descartada e "
                "esses candidatos recebem um avaliador a menos.\n"
            )
        else:
            print(
                "aviso: "
                + ", ".join(sobrepostos)
                + " avaliam as próprias respostas (às cegas). Registre o viés de "
                "auto-preferência como ameaça à validade.\n"
            )

    pendentes = feitos = falhos = 0
    for run_dir in execucoes:
        candidato = run_dir.parent.parent.name
        caso = run_dir.parent.name
        execucao = run_dir.name

        for juiz in juizes_de(candidato):
            destino = JUDGMENTS / f"{candidato}__{caso}__{execucao}__{juiz}.json"
            if destino.exists():
                continue
            pendentes += 1
            if args.dry_run:
                print(f"  pendente: {destino.name}")
                continue

            resposta, scrubs = montar_resposta(run_dir)
            try:
                resultado = avaliar(resposta, juiz)
            except Exception as exc:  # noqa: BLE001
                falhos += 1
                print(f"  FALHOU  {destino.name}: {exc}")
                continue

            resultado |= {
                "candidato": candidato,
                "caso": caso,
                "execucao": int(execucao.removeprefix("exec-")),
                "autoavaliacao": juiz == candidato,
                "marcas_removidas": scrubs,
                "caracteres_avaliados": len(resposta),
            }
            destino.write_text(
                json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            feitos += 1
            print(f"  ok      {destino.name}  nota={resultado['nota_final']:.2f}")

    if args.dry_run:
        print(f"\n{pendentes} julgamento(s) pendente(s)")
    else:
        print(f"\n{feitos} gravado(s), {falhos} falha(s), de {pendentes} pendente(s)")


if __name__ == "__main__":
    main()
