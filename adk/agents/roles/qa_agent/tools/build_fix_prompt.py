from typing import Optional
from .log_parser_tool import parse_pytest_log
 
 
# ── builders de prompt ────────────────────────────────────────────────────────
 
def _secao(titulo: str, conteudo: str) -> str:
    """Formata seção do prompt com título e conteúdo.

    Args:
        titulo: Título da seção.
        conteudo: Conteúdo da seção.

    Returns:
        str: Seção formatada com separadores.
    """
    linha = "─" * 60
    return f"{linha}\n{titulo}\n{linha}\n{conteudo.strip()}\n"
 
 
def build_fix_prompt(
    error_description: str,
    original_code: Optional[str] = None,
    test_code: Optional[str] = None,
    context: Optional[str] = None,
    language: str = "Python",
) -> str:
    """Constrói prompt estruturado para agente de correção de código.

    Args:
        error_description: Descrição do erro ou traceback.
        original_code: Código original a ser corrigido (opcional).
        test_code: Código dos testes que falharam (opcional).
        context: Informações adicionais de contexto (opcional).
        language: Linguagem de programação. Padrão: "Python".

    Returns:
        str: Prompt estruturado para o agente de correção.
    """
    secoes = []
 
    secoes.append(_secao(
        "🎯 PAPEL",
        (
            f"Você é um agente especialista em correção de código {language}. "
            "Sua tarefa é analisar o erro reportado, entender a causa raiz e "
            "reescrever o código corrigido — mantendo a lógica original intacta "
            "e garantindo que todos os testes passem."
            "Se não conseguir identificar com totalidade a parte do código que produz o erro, não tente mudar o código, mas produza um doubt artifact para revisão humana"
        )
    ))
 
    # Erro
    secoes.append(_secao(
        "🐛 ERRO REPORTADO",
        error_description
    ))
 
    # Código original (se fornecido)
    if original_code:
        secoes.append(_secao(
            "📄 CÓDIGO ORIGINAL",
            f"```{language.lower()}\n{original_code}\n```"
        ))
 
    # Testes que falharam (se fornecidos)
    if test_code:
        secoes.append(_secao(
            "🧪 TESTES QUE FALHARAM",
            f"```{language.lower()}\n{test_code}\n```"
        ))
 
    # Contexto adicional (se fornecido)
    if context:
        secoes.append(_secao(
            "📌 CONTEXTO ADICIONAL",
            context
        ))
 
    # Instruções de saída
    secoes.append(_secao(
        "📋 INSTRUÇÕES",
        (
            "1. Identifique a causa raiz do erro com base nas informações acima.\n"
            "2. Explique brevemente o que estava errado (máximo 3 linhas).\n"
            "3. Reescreva APENAS o trecho ou função que precisa ser corrigido.\n"
            "4. Não altere partes do código que não estão relacionadas ao erro.\n"
            "5. Garanta que o código corrigido seja compatível com os testes fornecidos.\n"
            "6. Retorne o código corrigido dentro de um bloco de código com a linguagem especificada."
        )
    ))
 
    # Formato de saída esperado
    secoes.append(_secao(
        "📤 FORMATO DE SAÍDA ESPERADO",
        (
            "**Causa do erro:** <explicação curta>\n\n"
            "**Linhas modificadas:**\n"
            f"**Código corrigido:**\n"
            f"```{language.lower()}\n"
            "<código corrigido aqui>\n"
            "```"
        )
    ))
 
    return "\n".join(secoes)
 
 
# ── funções de tool ───────────────────────────────────────────────────────────
 
def build_fix_prompt_from_error(
    error_description: str,
    original_code: Optional[str] = None,
    test_code: Optional[str] = None,
    context: Optional[str] = None,
    language: str = "Python",
) -> dict:
    """Gera prompt de correção a partir de descrição textual de erro.

    Args:
        error_description: Descrição do erro ou traceback.
        original_code: Código original (opcional).
        test_code: Testes que falharam (opcional).
        context: Contexto adicional (opcional).
        language: Linguagem de programação. Padrão: "Python".

    Returns:
        dict: Prompt gerado e metadados (language, prompt_length, etc.).
    """
    prompt = build_fix_prompt(
        error_description=error_description,
        original_code=original_code,
        test_code=test_code,
        context=context,
        language=language,
    )
 
    return {
        "prompt": prompt,
        "metadata": {
            "language": language,
            "has_original_code": original_code is not None,
            "has_test_code": test_code is not None,
            "has_context": context is not None,
            "prompt_length": len(prompt),
        }
    }
 
def build_fix_prompt_from_pytest(
    traceback_text: str,
    original_code: Optional[str] = None,
    test_code: Optional[str] = None,
    language: str = "Python",
) -> dict:
    """Gera prompt de correção a partir de traceback pytest.

    Args:
        traceback_text: Texto completo do traceback do pytest.
        original_code: Código original (opcional).
        test_code: Testes que falharam (opcional).
        language: Linguagem de programação. Padrão: "Python".

    Returns:
        dict: Prompt gerado e metadados.

    Note:
        Usa internamente parse_pytest_log para extrair informações estruturadas.
    """

    pytest_parsed = parse_pytest_log(traceback_text)

    error_description = (
        f"Arquivo:   {pytest_parsed.get('file', 'unknown')}\n"
        f"Linha:     {pytest_parsed.get('line', 'unknown')}\n"
        f"Função:    {pytest_parsed.get('function', 'unknown')}\n"
        f"Tipo:      {pytest_parsed.get('error_type', 'unknown')}\n"
        f"Assertion: {pytest_parsed.get('assertion', 'N/A')}\n"
        f"Mensagem:  {pytest_parsed.get('error_message', 'N/A')}\n\n"
        f"Traceback completo:\n{pytest_parsed.get('raw', '')}"
    )

    context = (
        f"Erro de teste detectado no arquivo {pytest_parsed.get('file', 'unknown')} "
        f"na função {pytest_parsed.get('function', 'unknown')} "
        f"(linha {pytest_parsed.get('line', 'unknown')}). "
        f"O tipo de erro é {pytest_parsed.get('error_type', 'unknown')}."
    )

    return build_fix_prompt_from_error(
        error_description=error_description,
        original_code=original_code,
        test_code=test_code,
        context=context,
        language=language,
    )
    raise ValueError(f"Tool '{tool_name}' não encontrada.")