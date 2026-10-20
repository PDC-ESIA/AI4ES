"""Sanitização e validação sintática do código pytest gerado pelo LLM."""

import ast
import logging
import re

from shared.security import validar_seguranca_codigo

logger = logging.getLogger("qa_agent")


def _validar_e_sanitizar_codigo(codigo: str, id_artefato: str) -> str:
    """Sanitiza tokens fora-da-gramática Python e valida via ast.parse.

    Aplica regex que remove placeholders entre `<>` colocados após keywords
    Python (pass<X>, return<Y>, etc.) e em seguida valida o código com
    ast.parse. Se mesmo após sanitização o código permanece inválido,
    levanta ValueError — o chamador propaga o erro para o autocorrect cycle.

    Depois da validação sintática, varre o código por riscos de segurança
    (leitura de ambiente, execução de processo/código dinâmico, rede fora de
    loopback, credenciais literais — ver shared.security) antes de liberar o
    código para ser persistido em disco e executado pelo pytest_runner.
    Defesa em profundidade complementar ao allowlist de ambiente do
    pytest_runner (P0): mesmo que algo passe por aqui, o subprocess já roda
    sem acesso às credenciais do processo pai.

    Args:
        codigo: String com código Python emitido pelo LLM.
        id_artefato: ID do artefato (usado nas mensagens de log/erro).

    Returns:
        Código Python sanitizado e validado.

    Raises:
        ValueError: Se ast.parse falha após sanitização, ou se o código
            apresentar risco de segurança.
    """
    padrao = re.compile(r'\b(pass|return|continue|break|raise)<[^>\n]*>')
    sanitizado = padrao.sub(r'\1', codigo)

    if sanitizado != codigo:
        logger.warning(
            f"[QA] Sanitização aplicada em {id_artefato}: "
            f"removidos placeholders fora da gramática Python."
        )

    try:
        ast.parse(sanitizado)
    except SyntaxError as e:
        raise ValueError(
            f"Código gerado para {id_artefato} é inválido após sanitização: "
            f"{e.msg} (linha {e.lineno}). Será reciclado via autocorrect."
        ) from e

    validar_seguranca_codigo(sanitizado, id_artefato)

    return sanitizado
