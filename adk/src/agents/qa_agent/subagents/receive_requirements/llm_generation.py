"""Chamadas ao LLM (via litellm) para parsing de requisitos fragmentados e geração de código pytest."""

import json
import os
from pathlib import Path

import litellm
from litellm import completion

from shared.llm import copilot_completion_kwargs

# Garante compatibilidade com providers que não suportam response_format
# (ex.: github_copilot). Precisa estar antes de qualquer chamada a completion().
litellm.drop_params = True


DEFAULT_SYSTEM_PROMPT = "Você gera exclusivamente código de teste pytest executável."

DEFAULT_GENERATION_RULES = """Regras obrigatórias:
- Retorne apenas código Python, sem markdown.
- Use pytest.
- O teste deve ser executável mesmo sem instalação de módulos externos ao diretório local.
- Se houver arquivo-fonte local, importe exclusivamente da cópia materializada
  junto ao teste. Não manipule sys.path; o conftest.py do QA faz isso.
- Se não houver código-fonte importável, gere testes de contrato (validações e comportamentos inferíveis) sem import quebrado.
- Cubra cenários feliz, inválido e borda.
- Inclua asserts objetivos.
- Cada função de teste deve ter corpo NÃO-VAZIO: ou uma docstring (modo
  esqueleto), ou asserts objetivos (modo completo). Nunca emita 'pass'
  isolado, 'TODO', placeholders entre <>, ou caracteres fora da gramática Python.
"""


def _parse_fragmented_requirements(raw_input: str) -> list:
    """Converte texto livre/fragmentado em uma lista estruturada de artefatos."""
    prompt = f"""Extraia os requisitos do texto abaixo e retorne um JSON array estrito no formato:
[{{ "id_artefato": "RF-001", "tipo": "RF", "conteudo": "...", "modulo": "...", "criticidade": "alta|media|baixa" }}]
Identifique os tipos (RF, RNF, HU, UC, RN). Se não houver ID claro, gere um sequencial.
Texto bruto: {raw_input}
"""
    model_name = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")
    llm_kwargs = copilot_completion_kwargs(model_name)
    if "/" not in model_name:
        model_name = f"gemini/{model_name}"
        llm_kwargs["api_key"] = os.environ.get("GOOGLE_API_KEY")
    response = completion(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        **llm_kwargs,
    )

    conteudo = response.choices[0].message.content.strip()
    # Limpa possíveis formatações markdown do retorno do LLM
    if conteudo.startswith("```json"):
        conteudo = conteudo.replace("```json\n", "").replace("```", "")
    return json.loads(conteudo)


def _gerar_pytest_via_llm(
    id_artefato: str,
    tipo: str,
    conteudo: str,
    modulo: str,
    arquivos_apoio: list[Path],
    nome_teste: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    generation_rules: str = DEFAULT_GENERATION_RULES,
) -> str:
    """Gera código pytest usando LLM a partir de artefato de requisito.

    Args:
        id_artefato: Identificador do artefato.
        tipo: Tipo do artefato (RF, HU, UC, RNF, RN).
        conteudo: Conteúdo do requisito.
        modulo: Módulo alvo do teste.
        arquivos_apoio: Lista de paths de arquivos de apoio.
        nome_teste: Nome do arquivo de teste a gerar.
        system_prompt: Mensagem de sistema enviada ao LLM.
        generation_rules: Bloco de regras injetado no final do prompt.

    Returns:
        str: Código Python do teste pytest.

    Raises:
        ValueError: Se o modelo retornar conteúdo vazio.
    """
    model_name = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")
    llm_kwargs = copilot_completion_kwargs(model_name)
    if "/" not in model_name:
        model_name = f"gemini/{model_name}"
        llm_kwargs["api_key"] = os.environ.get("GOOGLE_API_KEY")
    arquivos_textos = []
    for p in arquivos_apoio:
        try:
            texto = p.read_text(encoding="utf-8")
            arquivos_textos.append(f"--- {p.as_posix()} ---\n{texto}\n")
        except Exception:
            arquivos_textos.append(f"- {p.name} (Arquivo binário ou ilegível)")

    arquivos_desc = "\n".join(arquivos_textos)
    contexto_arquivos = (
        "Arquivos de apoio e CÓDIGO FONTE fornecidos para o teste:\n"
        f"{arquivos_desc}\n"
        if arquivos_desc
        else "Nenhum arquivo de apoio ou código fonte foi fornecido.\n"
    )
    tem_codigo = any(p.suffix in ['.py', '.java', '.js', '.c'] for p in arquivos_apoio)

    if tem_codigo:
        instrucao_geracao = (
            "O usuário forneceu o código fonte junto aos requisitos. "
            "MAPEAMENTO: Mapeie os cenários de teste contra as funções e métodos reais presentes no código. "
            "Gere os testes pytest COMPLETOS e integrados, utilizando asserts que validem as lógicas existentes. "
            "REGRA DE IMPORTAÇÃO MANDATÓRIA: os fontes são materializados junto ao teste e o conftest.py configura os imports. "
            "Se o path contiver `/src/modulo.py`, importe como `from src.modulo import funcao`. "
            "Não altere sys.path e nunca referencie workspace_output/coder."
        )
    else:
        instrucao_geracao = (
            "Nenhum código fonte foi fornecido — gere em MODO ESQUELETO. "
            "Use @pytest.mark.skip(reason='Aguardando implementação do código fonte') "
            "antes de cada função de teste. O corpo deve ter apenas uma docstring "
            "descrevendo o comportamento esperado. NÃO use 'pass' — a docstring é "
            "o corpo válido da função em Python."
        )

    prompt = f"""Gere SOMENTE código Python válido para {nome_teste}.
Artefato: {id_artefato}
Tipo: {tipo}
Módulo alvo: {modulo}
Requisito: {conteudo}

{contexto_arquivos}

DIRETRIZ DE GERAÇÃO CONDICIONAL:
{instrucao_geracao}

{generation_rules}
"""

    response = completion(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        **llm_kwargs,
    )

    codigo = ""
    choices = getattr(response, "choices", None)
    if choices and len(choices) > 0:
        message = getattr(choices[0], "message", None)
        codigo = getattr(message, "content", "") if message else ""

    if not codigo and isinstance(response, dict):
        response_choices = response.get("choices", [])
        if response_choices:
            codigo = response_choices[0].get("message", {}).get("content", "")

    if not isinstance(codigo, str) or not codigo.strip():
        raise ValueError("Modelo retornou conteúdo vazio para geração de pytest.")

    return codigo.strip() + "\n"
