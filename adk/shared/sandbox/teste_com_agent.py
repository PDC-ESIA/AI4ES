import asyncio
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from shared.agent_factory import create_se_agent, _make_bound_closure
from shared.sandbox.session_sandbox import get_agent_sandbox_path
from shared.sandbox.filesystem_daytona_criar_arquivo import tool_criar_arquivo_daytona


async def main():
    caminho_agente = get_agent_sandbox_path("coder_agent")  # -> "workspace/coder"
    tool_bound = FunctionTool(
        _make_bound_closure(tool_criar_arquivo_daytona, "base_dir", caminho_agente)
    )

    agente_teste = create_se_agent(
        name="teste_daytona",
        description="Agente de teste da PoC de sandbox",
        instruction=(
            "Você cria arquivos quando solicitado, usando a ferramenta "
            "disponível. Seja direto e conciso."
        ),
        tools=[tool_bound],
        # SEM agent_subdir aqui — já grudamos base_dir manualmente acima,
        # não queremos que a factory tente injetar de novo com caminho local.
    )

    runner = InMemoryRunner(agent=agente_teste)
    eventos = await runner.run_debug(
        "Crie um arquivo chamado ola.py com o conteúdo: print('Olá do sandbox via agente ADK')",
        verbose=True,
    )
    print("\n=== Total de eventos ===", len(eventos))

asyncio.run(main())