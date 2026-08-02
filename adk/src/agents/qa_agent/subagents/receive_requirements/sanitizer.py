"""Sanitização e validação sintática do código pytest gerado pelo LLM."""

import ast
import logging
import re

logger = logging.getLogger("qa_agent")


def _validar_e_sanitizar_codigo(codigo: str, id_artefato: str) -> str:
    """Sanitiza tokens fora-da-gramática Python e valida via ast.parse.

    Aplica regex que remove placeholders entre `<>` colocados após keywords
    Python (pass<X>, return<Y>, etc.) e em seguida valida o código com
    ast.parse. Se mesmo após sanitização o código permanece inválido,
    levanta ValueError — o chamador propaga o erro para o autocorrect cycle.

    Args:
        codigo: String com código Python emitido pelo LLM.
        id_artefato: ID do artefato (usado nas mensagens de log/erro).

    Returns:
        Código Python sanitizado e validado.

    Raises:
        ValueError: Se ast.parse falha após sanitização.
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

    return sanitizado
