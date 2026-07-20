import asyncio
import os
from daytona import AsyncDaytona, DaytonaConfig

async def main():
    config = DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"])

    async with AsyncDaytona(config) as daytona:
        sandbox = await daytona.create()
        try:
            caminho = "/home/daytona/workspace/teste.md"
            await sandbox.fs.upload_file(b"conteudo de teste", caminho)

            conteudo = await sandbox.fs.download_file(caminho)
            print(conteudo.decode("utf-8"))
        finally:
            await sandbox.delete()

asyncio.run(main())