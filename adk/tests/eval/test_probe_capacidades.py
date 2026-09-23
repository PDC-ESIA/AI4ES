"""Probe: o que a avaliação do ADK realmente enxerga com o nosso stack.

Não é gate de comportamento do pipeline — é verificação da própria ferramenta.
Roda uma avaliação instrumentada (métrica `ai4es_sonda`, que nunca reprova) e
inspeciona o objeto `Invocation` que o ADK entregou às métricas.

A pergunta que ele responde é o achado **U3** da §2-A do `PLANO_POC.md`:
`Invocation.app_details.agent_details[].instructions` e `.tool_declarations` são
populados pelo `_RequestIntercepterPlugin` a partir do `LlmRequest` real. Se isso
valer com `LiteLlm`/`github_copilot` — e não só com Gemini —, abre-se a
possibilidade de assertar sobre **o prompt renderizado**, que é o buraco da PP3
(21 `prompt.py`, 5.247 linhas, zero testes).

O teste passa em qualquer cenário: o resultado é o relatório impresso. O que ele
não deixa passar é a mecânica quebrada.
"""

import pytest

from tests.eval import metrics

MODULO_VALIDATOR = "src.agents.implementation_validator"


@pytest.mark.eval
async def test_o_que_a_avaliacao_enxerga(workspace_semeado, evalset, rodar_eval):
    workspace_semeado("validator_verde")
    caminho = evalset("sonda_app_details")

    metrics.limpar_captura()
    await rodar_eval(caminho, agent_module=MODULO_VALIDATOR, num_runs=1)

    assert metrics.CAPTURA, (
        "A sonda não capturou nenhuma invocação. A métrica custom não foi "
        "chamada — confira o registro em conftest e o bloco custom_metrics."
    )

    print("\n" + "=" * 78)
    print("PROBE — o que o AgentEvaluator entrega às métricas")
    print("=" * 78)

    tem_app_details = False
    tem_instructions = False
    for i, registro in enumerate(metrics.CAPTURA, 1):
        print(f"\n[invocação {i}] id={registro['invocation_id']}")
        print(f"  tools chamadas      : {registro['tools_chamadas']}")
        print(f"  app_details presente: {registro['app_details_presente']}")
        tem_app_details |= registro["app_details_presente"]

        for nome, detalhe in registro["agentes"].items():
            tem_instructions |= detalhe["tem_instructions"]
            print(f"  agente '{nome}'")
            print(f"    instructions      : {detalhe['tamanho_instructions']} chars")
            print(f"    tools declaradas  : {detalhe['tools_declaradas']}")
        print(f"  resposta final ({len(registro['resposta_final'])} chars):")
        print("    " + registro["resposta_final"][:400].replace("\n", "\n    "))

    print("\n" + "-" * 78)
    print("VEREDITO DO PROBE (achado U3 do PLANO_POC §2-A)")
    print(f"  app_details populado com LiteLlm : {tem_app_details}")
    print(f"  instruction renderizada visível  : {tem_instructions}")
    if tem_instructions:
        print("  => Dá para assertar sobre o PROMPT renderizado por métrica custom,")
        print("     sem servidor web e sem adk conformance. Gancho para a PP3.")
    else:
        print("  => NÃO dá. Para regressão de prompt resta o adk conformance (U1+U2),")
        print("     que exige servidor em 127.0.0.1:8000 e plugins registrados.")
    print("=" * 78)
