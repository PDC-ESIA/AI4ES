"""
teste_linter.py
===============
Verificações estáticas de qualidade de código executadas localmente ou no CI
**antes** de acionar o agente LLM.  Falhar aqui é rápido e gratuito — evita
consumir tokens da API Mistral em diffs que já têm problemas óbvios de estilo.

Checks executados
-----------------
1. Arquivos Python modificados passam pelo flake8 (PEP-8 + erros de sintaxe).
2. Nenhum arquivo Python modificado contém `print(` fora de scripts de entrada
   (heurística simples: apenas validador.py e main.py podem ter prints).
3. Nenhum arquivo Python modificado importa `LlmRequest` diretamente
   (uso incorreto identificado em versões anteriores do validador).

Uso
---
    uv run python teste_linter.py            # verifica todos os .py do projeto
    uv run python teste_linter.py arquivo.py # verifica arquivo específico
"""

import subprocess
import sys
import os
from pathlib import Path

# Arquivos que podem conter print() legitimamente (scripts de CLI/entrada).
ARQUIVOS_COM_PRINT_PERMITIDO = {"validador.py", "main.py", "test_linter.py"}

# Importações proibidas e a razão de cada uma.
IMPORTACOES_PROIBIDAS = {
    "from google.adk.models.llm_request import LlmRequest": (
        "Use Runner + InMemorySessionService para acionar agentes ADK. "
        "LlmRequest é interno ao framework e não expõe a interface de sessão."
    ),
}


def coletar_arquivos_python(raiz: Path) -> list[Path]:
    """Retorna todos os .py sob `raiz`, excluindo .venv e __pycache__."""
    return [
        p
        for p in raiz.rglob("*.py")
        if ".venv" not in p.parts and "__pycache__" not in p.parts
    ]


def verificar_flake8(arquivos: list[Path]) -> list[str]:
    """Executa flake8 nos arquivos e retorna lista de violações."""
    if not arquivos:
        return []

    resultado = subprocess.run(
        ["flake8", "--max-line-length=100", "--extend-ignore=E203,W503"]
        + [str(f) for f in arquivos],
        capture_output=True,
        text=True,
    )
    linhas = resultado.stdout.strip().splitlines()
    return linhas  # lista vazia se tudo OK


def verificar_importacoes_proibidas(arquivos: list[Path]) -> list[str]:
    """Detecta importações que foram identificadas como incorretas no projeto."""
    violacoes = []
    for arquivo in arquivos:
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except OSError:
            continue
        for importacao, motivo in IMPORTACOES_PROIBIDAS.items():
            if importacao in conteudo:
                violacoes.append(
                    f"{arquivo}: importação proibida '{importacao}' — {motivo}"
                )
    return violacoes


def verificar_prints_indevidos(arquivos: list[Path]) -> list[str]:
    """Detecta uso de print() em módulos que não deveriam ter saída direta."""
    violacoes = []
    for arquivo in arquivos:
        if arquivo.name in ARQUIVOS_COM_PRINT_PERMITIDO:
            continue
        try:
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for numero, linha in enumerate(linhas, start=1):
            linha_sem_comentario = linha.split("#")[0]
            if "print(" in linha_sem_comentario:
                violacoes.append(
                    f"{arquivo}:{numero}: print() detectado em módulo de biblioteca "
                    f"— use logging em vez de print()."
                )
    return violacoes


def main() -> None:
    raiz = Path(__file__).parent.parent.parent

    # Se arquivos foram passados como argumento, usa apenas eles; senão, varre tudo.
    if len(sys.argv) > 1:
        arquivos = [Path(a) for a in sys.argv[1:] if a.endswith(".py")]
    else:
        arquivos = coletar_arquivos_python(raiz)

    print(f"Verificando {len(arquivos)} arquivo(s) Python...\n")

    erros: list[str] = []

    # 1. flake8
    violacoes_flake8 = verificar_flake8(arquivos)
    if violacoes_flake8:
        erros.append("=== Violações de estilo (flake8) ===")
        erros.extend(violacoes_flake8)

    # 2. Importações proibidas
    violacoes_import = verificar_importacoes_proibidas(arquivos)
    if violacoes_import:
        erros.append("\n=== Importações proibidas ===")
        erros.extend(violacoes_import)

    # 3. Prints indevidos
    violacoes_print = verificar_prints_indevidos(arquivos)
    if violacoes_print:
        erros.append("\n=== Uso de print() em módulos de biblioteca ===")
        erros.extend(violacoes_print)

    if erros:
        print("\n".join(erros))
        print(
            f"\n{len(erros)} problema(s) encontrado(s). Corrija antes de submeter o PR."
        )
        sys.exit(1)
    else:
        print("Nenhuma violação encontrada. Código aprovado pelo linter.")
        sys.exit(0)


if __name__ == "__main__":
    main()
