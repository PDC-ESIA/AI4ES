"""Simula N "execuções" do reviewer sem rodar o pipeline de agentes.

Chama diretamente o mesmo código que `reviewer/agent.py::_escrever_memoria`
usa (`_entradas_brutas`, `registrar_erros`, `_filtrar_recorrentes`,
`_formatar_licao_lote`, `get_memory().add()`), com um `error_history`
fabricado, mas no formato exato de um `ErrorReport.model_dump()` real.

Serve pra validar o mecanismo de lote (Testes A/B) e a troca de backend
(Postgres vs Chroma) contra o banco de verdade, em segundos — sem esperar
minutos de LLM (requisitos/design/codificação) só pra chegar na parte que
importa pra esse teste. Respeita as mesmas env vars da aplicação real
(AI4ES_MEMORY_ENABLED, AI4ES_MEMORY_USE_POSTGRES, etc.) — configure o
`.env` como for testar antes de rodar.

Uso — Teste A (3 execuções com o MESMO erro, deve virar lição):
    uv run python scripts/mem0_batch_simulation.py --stack python --reset \
        --erro "implantacao_artefato:FALHA_BUILD" \
        --erro "implantacao_artefato:FALHA_BUILD" \
        --erro "implantacao_artefato:FALHA_BUILD"

Uso — Teste B (3 execuções com erros DIFERENTES, nada deve virar lição):
    uv run python scripts/mem0_batch_simulation.py --stack python --reset \
        --erro "implantacao_artefato:FALHA_BUILD" \
        --erro "testes_automatizados:FALHA_TESTE" \
        --erro "inicializacao_aplicacao:PORTA_OCUPADA"

--reset limpa só o log local pendente (arquivo) antes de começar — não
mexe no que já está gravado no mem0. Use --reset-memoria pra também
apagar as lições já gravadas no mem0 para a stack (equivalente ao
TRUNCATE/delete_all manual).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.memory.config import get_memory, memoria_habilitada  # noqa: E402
from shared.memory.error_log import (  # noqa: E402
    ler_erros_pendentes,
    limite_lote,
    limpar_erros_pendentes,
    registrar_erros,
)
from src.agents.workflow_coding_review.reviewer.agent import (  # noqa: E402
    _entradas_brutas,
    _filtrar_recorrentes,
    _formatar_licao_lote,
)


def _construir_error_history(estagio: str, codigo: str, iteracao: int) -> list[dict]:
    """Mesmo formato de `ErrorReport.model_dump()` — ver executor/schemas.py."""
    return [
        {
            "work_item_id": "SIMULACAO-001",
            "iteration": iteracao,
            "verdict_status": "reprovado",
            "blocking_reason": f"Falha simulada: {codigo}",
            "failed_criteria": [],
            "failed_stages": [
                {
                    "stage": estagio,
                    "status": "falha",
                    "error_code": codigo,
                    "summary": f"Falha simulada em {estagio}",
                    "evidence": {},
                }
            ],
            "report_path": None,
        }
    ]


async def _simular_execucao(
    stack: str, estagio: str, codigo: str, iteracao: int
) -> None:
    print(f"\n--- Execução simulada {iteracao} — erro: {estagio}:{codigo} ---")

    if not memoria_habilitada():
        print(
            "AI4ES_MEMORY_ENABLED não é 'true' — nada é feito (correto, é o interruptor geral)."
        )
        return

    error_history = _construir_error_history(estagio, codigo, iteracao)
    novas_entradas = _entradas_brutas(error_history, stack)
    registrar_erros(stack, novas_entradas)

    pendentes = ler_erros_pendentes(stack)
    print(f"Pendentes após esta execução: {len(pendentes)}/{limite_lote()}")

    if len(pendentes) < limite_lote():
        print("Abaixo do limite — só acumulou, nada enviado ao mem0.")
        return

    recorrentes = _filtrar_recorrentes(pendentes)
    if recorrentes:
        licao = _formatar_licao_lote(recorrentes)
        print(
            f"Lote bateu o limite. {len(recorrentes)} entrada(s) recorrente(s) "
            "— gravando no mem0:"
        )
        print(f"  {licao!r}")
        await get_memory().add(messages=licao, agent_id=stack)
        print("Gravado com sucesso.")
    else:
        print(
            "Lote bateu o limite, mas nada se repetiu — descartado, nenhuma lição gravada."
        )

    limpar_erros_pendentes(stack)


async def _run(
    stack: str, erros: list[str], resetar: bool, resetar_memoria: bool
) -> int:
    if resetar_memoria:
        await get_memory().delete_all(agent_id=stack)
        print(f"Lições já gravadas no mem0 para a stack {stack!r} foram apagadas.")

    if resetar:
        limpar_erros_pendentes(stack)
        print(f"Log pendente da stack {stack!r} zerado antes de começar.")

    for i, erro in enumerate(erros, start=1):
        estagio, _, codigo = erro.partition(":")
        await _simular_execucao(stack, estagio.strip(), codigo.strip(), i)

    try:
        resultado = await get_memory().search(
            query=stack, filters={"agent_id": stack}, top_k=10
        )
        memorias = resultado.get("results", [])
        print(
            f"\n{len(memorias)} lição(ões) atualmente no mem0 para a stack {stack!r}:"
        )
        for m in memorias:
            print(f"  - {m.get('memory')}")
    except Exception as exc:
        print(f"\nNão foi possível consultar o mem0 para confirmar: {exc}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--stack", default="python")
    parser.add_argument(
        "--erro",
        action="append",
        required=True,
        help="Formato 'estagio:codigo_erro'. Repita a flag uma vez por execução simulada.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Limpa o log local pendente da stack antes de começar.",
    )
    parser.add_argument(
        "--reset-memoria",
        action="store_true",
        help="Também apaga as lições já gravadas no mem0 para a stack antes de começar.",
    )
    args = parser.parse_args()
    return asyncio.run(_run(args.stack, args.erro, args.reset, args.reset_memoria))


if __name__ == "__main__":
    raise SystemExit(main())
