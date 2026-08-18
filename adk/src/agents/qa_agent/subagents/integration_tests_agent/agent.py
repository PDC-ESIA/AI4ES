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
    workspace_agent="integration_tests_agent",
    agent_label="integration_tests_agent",
    system_prompt="Você gera exclusivamente código pytest executável de testes de integração.",
    generation_rules="""Você é um gerador de TESTES DE INTEGRAÇÃO. Os testes devem validar a colaboração
entre dois ou mais componentes reais do sistema — por exemplo, API/serviço,
serviço/repositório, persistência, filas ou adaptadores — conforme o requisito e
os arquivos fornecidos. Não produza testes unitários isolados de uma única função.

Regras obrigatórias:
- Retorne apenas código Python, sem markdown.
- Use pytest.
- Prefira fixtures para preparar e limpar estado, dados e dependências locais.
- Exercite interfaces públicas e o fluxo entre componentes; valide o resultado
  observável da integração com asserts objetivos.
- Não use mocks para substituir os componentes internos que constituem a
  integração. Somente isole serviços realmente externos ou indisponíveis quando
  isso for indispensável, documentando-o em comentário.
- O teste deve ser executável mesmo sem módulos externos ao diretório local.
- Se houver arquivos-fonte locais, importe-os de forma explícita e relativa,
  ajustando pathlib/sys.path para a própria pasta do teste quando necessário.
- Se não houver código ou infraestrutura suficiente para executar a integração,
  gere um esqueleto com @pytest.mark.skip e uma docstring que descreva a
  integração pendente; não crie imports quebrados.
- Cubra cenário feliz, inválido e de borda, quando aplicáveis ao fluxo integrado.
- Cada função de teste deve ter corpo NÃO-VAZIO: docstring no modo esqueleto,
  ou fixtures/asserts objetivos no modo completo. Nunca emita 'pass' isolado,
  'TODO', placeholders entre <>, ou caracteres fora da gramática Python.""",
)
_builder = TestBuilder(_CONFIG)

agent = LlmAgent(
    name="integration_tests_agent",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
    description=(
        "Subagente que recebe artefatos de requisito em JSON e gera testes de integração pytest "
        "funcionais em workspace_output/tests/integration_tests/."
    ),
    instruction=(
        "Você é o construtor de testes de integração. Ao receber uma mensagem do usuário, monte um JSON com os campos: "
        "id_artefato (ex: 'HU-001'), tipo ('HU'), conteudo, modulo ('geral' se não informado), criticidade ('alta'). "
        "MUITO IMPORTANTE: Se a requisição contiver código-fonte (em anexo ou no texto), você DEVE criar uma propriedade chamada 'arquivos_apoio' "
        "sendo uma lista de objetos com 'nome' (ex: arquivo.py) e 'conteudo' (o código completo). "
        "Se você não preencher 'arquivos_apoio', o sistema NÃO reconhecerá o código-fonte! "
        "No campo conteudo, inclua apenas o texto do requisito. "
        "Chame a tool receber_requisitos com o JSON gerado e retorne o resultado."
    ),
    tools=[FunctionTool(_builder.receber_requisitos)],
)

integration_tests_agent = agent

