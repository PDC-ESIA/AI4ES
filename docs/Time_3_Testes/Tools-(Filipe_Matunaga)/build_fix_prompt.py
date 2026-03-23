from typing import Optional
 
 
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
    Gera um prompt estruturado para um agente de correção de código a partir
    da descrição de um erro.
 
    Parâmetros:
        error_description (str): Descrição do erro, mensagem de exceção ou traceback.
        original_code (str, optional): Código-fonte que precisa ser corrigido.
        test_code (str, optional): Código dos testes que falharam.
        context (str, optional): Contexto adicional sobre o comportamento esperado.
        language (str): Linguagem de programação. Padrão: "Python".
 
    Retorna:
        dict com:
            - prompt (str): Prompt estruturado pronto para envio ao agente.
            - metadata (dict): Informações sobre o que foi incluído no prompt.
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
 
 
def build_fix_prompt_from_log_entry(
    log_entry: dict,
    original_code: Optional[str] = None,
    test_code: Optional[str] = None,
    language: str = "Python",
) -> dict:
    """
    Gera um prompt estruturado para um agente de correção de código a partir
    de uma entrada de log já parseada (retornada por parse_log_line ou parse_log_lines).
 
    Útil para encadear diretamente com as tools do log_parser_tool.
 
    Parâmetros:
        log_entry (dict): Entrada de log com os campos: level, module, message, timestamp, raw.
        original_code (str, optional): Código-fonte que precisa ser corrigido.
        test_code (str, optional): Código dos testes que falharam.
        language (str): Linguagem de programação. Padrão: "Python".
 
    Retorna:
        dict com:
            - prompt (str): Prompt estruturado pronto para envio ao agente.
            - metadata (dict): Informações sobre o que foi incluído no prompt.
    """
    error_description = (
        f"Nível:     {log_entry.get('level', 'UNKNOWN')}\n"
        f"Módulo:    {log_entry.get('module', 'unknown')}\n"
        f"Timestamp: {log_entry.get('timestamp', 'unknown')}\n"
        f"Mensagem:  {log_entry.get('message', '')}\n"
        f"Raw:       {log_entry.get('raw', '')}"
    )
 
    context = f"Formato do log detectado: {log_entry.get('format', 'unknown')}"
 
    return build_fix_prompt_from_error(
        error_description=error_description,
        original_code=original_code,
        test_code=test_code,
        context=context,
        language=language,
    )
 
 
# ── definição das tools para o agente ────────────────────────────────────────
 
CODE_FIX_PROMPT_TOOLS = [
    {
        "name": "build_fix_prompt_from_error",
        "description": (
            "Gera um prompt estruturado para um agente de correção de código "
            "a partir da descrição textual de um erro. "
            "O prompt resultante instrui o agente a identificar a causa raiz, "
            "explicar o problema e reescrever o código corrigido. "
            "Use quando tiver a mensagem de erro ou traceback em formato de texto."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "error_description": {
                    "type": "string",
                    "description": (
                        "Descrição do erro, mensagem de exceção ou traceback completo. "
                        "Ex: 'AssertionError: assert entry.module == \"auth\"' ou "
                        "um traceback completo do pytest."
                    )
                },
                "original_code": {
                    "type": "string",
                    "description": "Código-fonte que precisa ser corrigido (opcional)."
                },
                "test_code": {
                    "type": "string",
                    "description": "Código dos testes que falharam (opcional)."
                },
                "context": {
                    "type": "string",
                    "description": "Contexto adicional sobre o comportamento esperado (opcional)."
                },
                "language": {
                    "type": "string",
                    "description": "Linguagem de programação do código. Padrão: 'Python'."
                }
            },
            "required": ["error_description"]
        },
        "function": build_fix_prompt_from_error,
    },
    {
        "name": "build_fix_prompt_from_log_entry",
        "description": (
            "Gera um prompt estruturado para um agente de correção de código "
            "a partir de uma entrada de log já parseada. "
            "Encadeia diretamente com as tools do log_parser_tool — "
            "passe o dict retornado por parse_log_line como log_entry. "
            "Use quando o erro vier de um log estruturado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "log_entry": {
                    "type": "object",
                    "description": (
                        "Entrada de log parseada com os campos: "
                        "level, module, message, timestamp, raw, format. "
                        "Retornada por parse_log_line ou parse_log_lines."
                    )
                },
                "original_code": {
                    "type": "string",
                    "description": "Código-fonte que precisa ser corrigido (opcional)."
                },
                "test_code": {
                    "type": "string",
                    "description": "Código dos testes que falharam (opcional)."
                },
                "language": {
                    "type": "string",
                    "description": "Linguagem de programação do código. Padrão: 'Python'."
                }
            },
            "required": ["log_entry"]
        },
        "function": build_fix_prompt_from_log_entry,
    },
]
 
 
def execute_tool(tool_name: str, tool_input: dict):
    """
    Executa uma tool pelo nome, passando os inputs necessários.
    Use essa função no loop do agente para despachar chamadas de tool.
 
    Exemplo:
        result = execute_tool("build_fix_prompt_from_error", {
            "error_description": "AssertionError: assert entry.module == 'auth'",
            "original_code": "def parse_line(raw): ...",
            "test_code": "def test_modulo(entry): assert entry.module == 'auth'",
        })
    """
    for tool in CODE_FIX_PROMPT_TOOLS:
        if tool["name"] == tool_name:
            return tool["function"](**tool_input)
    raise ValueError(f"Tool '{tool_name}' não encontrada.")