import asyncio
import os
from daytona import AsyncDaytona, DaytonaConfig

async def main():
    config = DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"])

    async with AsyncDaytona(config) as daytona:
        sandbox = await daytona.create()
        try:
            # Teste 1: executar comando de shell
            resultado_shell = await sandbox.process.exec("echo 'ola do sandbox' && python3 --version")
            print("=== exec (shell) ===")
            print("exit_code:", resultado_shell.exit_code)
            print("result:", resultado_shell.result)

            # Teste 2: rodar código Python diretamente, sem criar arquivo
            resultado_code = await sandbox.process.code_run(
                "print(2 + 2)\nprint('rodando direto no sandbox')"
            )
            print("=== code_run (código direto) ===")
            print("exit_code:", resultado_code.exit_code)
            print("result:", resultado_code.result)

            # Teste 3: integração real com fs — criar um arquivo .py e EXECUTAR ele
            # (isso é o mais próximo do que o agente coder faz)
            await sandbox.fs.upload_file(
                b"print('Arquivo criado por uma tool e executado por outra')",
                "workspace/script_teste.py",
            )
            resultado_arquivo = await sandbox.process.exec("python3 workspace/script_teste.py")
            print("=== exec de um arquivo criado via fs ===")
            print("exit_code:", resultado_arquivo.exit_code)
            print("result:", resultado_arquivo.result)

            # Teste 4: deletar o arquivo criado
            arquivos_presentes = await sandbox.fs.list_files("workspace")
            print("Arquivos presentes em workspace/:", [f.name for f in arquivos_presentes])
            await sandbox.fs.delete_file("workspace/script_teste.py")
            arquivos_restantes = await sandbox.fs.list_files("workspace")
            print("=== delete_file ===")
            print("Arquivos restantes em workspace/:", [f.name for f in arquivos_restantes])

        finally:
            await sandbox.delete()

asyncio.run(main())