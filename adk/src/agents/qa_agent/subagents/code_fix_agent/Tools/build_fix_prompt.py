from typing import Optional
from .log_parser_tool import parse_pytest_log
 
 
# ── builders de prompt ────────────────────────────────────────────────────────
 
def _secao(titulo: str, conteudo: str) -> str:
    """Formata uma seção do prompt com título e conteúdo."""
    linha = "─" * 60
    return f"{linha}\n{titulo}\n{linha}\n{conteudo.strip()}\n"
 
 
def build_fix_prompt(
    error_description: str,
    original_code: Optional[str] = None,
    test_code: Optional[str] = None,
    context: Optional[str] = None,
    language: str = "Python",
) -> str:
    """
    Constrói um prompt estruturado para um agente de correção de código.
 
    Recebe a descrição do erro (e opcionalmente o código original, os testes
    que falharam e contexto adicional) e monta um prompt completo pronto para
    ser enviado a outro agente LLM.
 
    Parâmetros:
        error_description (str): Descrição do erro ou traceback capturado.
        original_code (str, optional): Código que precisa ser corrigido.
        test_code (str, optional): Código dos testes que falharam.
        context (str, optional): Informações adicionais de contexto (ex: comportamento esperado).
        language (str): Linguagem de programação do código. Padrão: "Python".
 
    Retorna:
        str: Prompt estruturado pronto para ser enviado ao agente de correção.
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
    """
    Gera um prompt estruturado para um agente de correção de código a partir da descrição textual de um erro. 
    O prompt resultante instrui o agente a identificar a causa raiz, 
    Explicar o problema e reescrever o código corrigido. 
    Use quando tiver a mensagem de erro ou traceback em formato de texto.
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
    """
    Gera um prompt estruturado para um agente de correção de código 
    a partir de um traceback completo de pytest. 
    Encadeia diretamente com parse_pytest_log — passe o texto do traceback. 
    Use quando o erro vier de um teste pytest que falhou.
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