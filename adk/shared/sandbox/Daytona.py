import asyncio
from google.adk.integrations.daytona import DaytonaEnvironment

async def main():
    env = DaytonaEnvironment(api_key="...")  # ou via env var DAYTONA_API_KEY
    await env.initialize()

    await env.write_file("workspace/teste.md", "conteúdo de teste")
    conteudo = await env.read_file("workspace/teste.md")
    print(conteudo)  # valida persistência antes de fechar

    await env.close()

asyncio.run(main())