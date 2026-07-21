import asyncio
from daytona import AsyncDaytona, DaytonaConfig
import os

async def main():
    config = DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"])

    with open("sandbox_id.txt") as f:
        sandbox_id = f.read().strip()

    async with AsyncDaytona(config) as daytona:
        sandbox = await daytona.get(sandbox_id)  # reconecta

        caminho = "/home/daytona/workspace/teste.md"
        conteudo = await sandbox.fs.download_file(caminho)
        print("Conteúdo recuperado:", conteudo.decode("utf-8"))
        
        await sandbox.delete()

asyncio.run(main())