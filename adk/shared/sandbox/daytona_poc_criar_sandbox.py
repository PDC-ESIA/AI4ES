import asyncio
import os
from daytona import AsyncDaytona, DaytonaConfig

async def main():
    config = DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"])

    async with AsyncDaytona(config) as daytona:
        sandbox = await daytona.create()

        caminho = "/home/daytona/workspace/teste.md"
        await sandbox.fs.upload_file(b"conteudo da primeira chamada", caminho)

        # Salva o ID localmente, simulando o que no futuro seria
        # tool_context.state["sandbox_id"] = sandbox.id
        with open("sandbox_id.txt", "w") as f:
            f.write(sandbox.id)

        print(f"Sandbox criado: {sandbox.id}")
        # Sem deletar — propositalmente, para simular fim de uma "chamada de tool"

asyncio.run(main())