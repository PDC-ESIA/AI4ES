import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from shared.tools.test_builder_common import (
    TestBuilder,
    TestBuilderConfig,
    _extrair_de_parts,
    _normalizar_anexos_inline,
    _ordenar_por_criticidade,
    _parse_fragmented_requirements,
    _run_async,
    _safe_filename,
    _salvar_arquivos_apoio,
    _slugify,
    _validar_artefato,
    _validar_e_sanitizar_codigo,
)

_CONFIG = TestBuilderConfig(
    workspace_agent="receive_requirements",
    agent_label="qa_agent",
    system_prompt="Você gera exclusivamente código de teste pytest executável.",
    generation_rules="""Regras obrigatórias:
- Retorne apenas código Python, sem markdown.
- Use pytest.
- O teste deve ser executável mesmo sem instalação de módulos externos ao diretório local.
- Se houver arquivo-fonte local, faça import relativo via pathlib/sys.path usando a própria pasta do teste.
- Se não houver código-fonte importável, gere testes de contrato (validações e comportamentos inferíveis) sem import quebrado.
- Cubra cenários feliz, inválido e borda.
- Inclua asserts objetivos.
- Cada função de teste deve ter corpo NÃO-VAZIO: ou uma docstring (modo
  esqueleto), ou asserts objetivos (modo completo). Nunca emita 'pass'
  isolado, 'TODO', placeholders entre <>, ou caracteres fora da gramática Python.""",
)
_builder = TestBuilder(_CONFIG)

agent = LlmAgent(
    name="receber_requisitos",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    description=(
        "Subagente que recebe artefatos de requisito em JSON e gera arquivos pytest "
        "funcionais em workspace_output/tests/inputs/."
    ),
    instruction=(
        "Ao receber uma mensagem do usuário, monte um JSON com os campos: "
        "id_artefato (ex: 'HU-001'), tipo ('HU'), conteudo, modulo ('geral' se não informado), criticidade ('alta'). "
        "MUITO IMPORTANTE: Se a requisição contiver código-fonte (em anexo ou no texto), você DEVE criar uma propriedade chamada 'arquivos_apoio' "
        "sendo uma lista de objetos com 'nome' (ex: arquivo.py) e 'conteudo' (o código completo). "
        "Se você não preencher 'arquivos_apoio', o sistema NÃO reconhecerá o código-fonte! "
        "No campo conteudo, inclua apenas o texto do requisito. "
        "Chame a tool receber_requisitos com o JSON gerado e retorne o resultado."
    ),
    tools=[FunctionTool(_builder.receber_requisitos)],
)
