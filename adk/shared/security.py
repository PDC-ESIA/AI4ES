"""Guardrails de segurança compartilhados entre agentes que executam código
ou repassam saída de subprocesso (stdout/stderr/tracebacks) para um LLM ou
para o usuário.

Consolida padrões que já existiam duplicados dentro do subagente E2E do QA
(`e2e_test_generator/tools/executar_playwright.py` e
`gerenciar_runtime_alvo.py`) para que outros fluxos — como o pytest_runner —
possam reutilizá-los em vez de reinventar.
"""

from __future__ import annotations

import os
import re


def redigir_segredos(texto: str) -> str:
    """Redige credenciais de um texto livre (logs, stdout, tracebacks).

    Uso pretendido: aplicar sobre qualquer saída de subprocesso ou de
    execução de código antes de propagá-la para outro LLM (ex.: prompt de
    correção), para o usuário (relatório final) ou para persistência (cache,
    doubt artifact). Não substitui uma allowlist de ambiente — trata do caso
    em que o segredo já vazou para dentro de um texto e precisa ser mascarado
    antes de propagar adiante.

    Cobre: header Authorization, tokens Bearer, pares chave=valor para
    api_key/access_token/token/password/secret, e credenciais embutidas em
    URL (https://user:senha@host).
    """
    texto = re.sub(
        r"(?i)\b(authorization\s*[:=]\s*)[^\r\n,;]+",
        r"\1[REDACTED]",
        texto,
    )
    texto = re.sub(
        r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer [REDACTED]",
        texto,
    )
    texto = re.sub(
        (
            r"(?i)\b(api[_-]?key|access[_-]?token|token|"
            r"password|passwd|secret)\b(\s*[:=]\s*)([^\s,;]+)"
        ),
        r"\1\2[REDACTED]",
        texto,
    )
    return re.sub(
        r"(https?://)([^/\s:@]+):([^@\s/]+)@",
        r"\1[REDACTED]@",
        texto,
        flags=re.IGNORECASE,
    )


_ALLOWLIST_PYTHON = {
    # Paridade com as allowlists do fluxo E2E (_ambiente_minimo_node /
    # _ambiente_minimo_runtime): variáveis de SO necessárias para o
    # interpretador/subprocesso inicializar corretamente.
    "SYSTEMROOT",
    "WINDIR",
    "PATH",
    "PATHEXT",
    "TEMP",
    "TMP",
    # Runtime Python.
    "PYTHONIOENCODING",
    "PYTHONUTF8",
    # Lidas por bibliotecas Python comuns (coverage, pip cache, etc.) para
    # resolver diretório de config/cache do usuário.
    "HOME",
    "USERPROFILE",
}


def ambiente_minimo_python(pythonpath: list[str] | None = None) -> dict[str, str]:
    """Allowlist de variáveis de ambiente para subprocessos Python.

    Evita expor credenciais do processo pai (ex.: GOOGLE_API_KEY,
    DATABASE_URL) a código gerado por LLM e executado via subprocess — mesmo
    padrão já usado no fluxo E2E (`_ambiente_minimo_runtime`).

    Uma variável da allowlist ausente no ambiente do host simplesmente não
    aparece no dict retornado (sem erro, sem string vazia).

    O PYTHONPATH do host NUNCA é herdado: se o chamador precisar de um
    PYTHONPATH no subprocesso, deve passá-lo explicitamente via
    `pythonpath`.
    """
    env = {
        chave: valor
        for chave in _ALLOWLIST_PYTHON
        if (valor := os.environ.get(chave)) is not None
    }
    env["PYTHONIOENCODING"] = "utf-8"
    if pythonpath:
        env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    return env
