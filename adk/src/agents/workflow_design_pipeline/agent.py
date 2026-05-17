import os
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from src.agents.design_architect.agent import agent as design_architect
from src.agents.mermaid_specialist.agent import agent as mermaid_specialist
from src.agents.markdown_specialist.agent import agent as markdown_specialist
from src.agents.validator.agent import agent as validator
from src.agents.io_agent.agent import agent as io_agent

_DEFAULT_MODEL = "gemini-2.5-flash"

_INSTRUCTION = """
Você é o pipeline de design de software.

PAPEL:
Orquestrar a execução sequencial dos agentes especialistas para transformar um lote de
Histórias de Usuário em diagramas Mermaid (.mmd) e relatórios Markdown (.md) validados
e persistidos em staging.

CONTRATO DE COMUNICAÇÃO ENTRE AGENTES:
Cada especialista persiste seu artefato via `save_artifact` (que escreve no subdir do
agente em `workspace_output/`) e retorna ao pipeline o CAMINHO ABSOLUTO do arquivo salvo
(campo `path` retornado por `save_artifact`), NÃO o conteúdo inline. Isso é intencional
para evitar duplicação de texto longo. **Aceite paths como sinal de sucesso**.

PROTOCOLO DE FILENAME PASSING (CRÍTICO):
Os especialistas têm bindings de workspace isolados (cada um vê apenas seu próprio subdir):
- design_architect escreve em `workspace_output/design/`
- mermaid_specialist escreve em `workspace_output/design/diagrams/`
- markdown_specialist escreve em `workspace_output/design/reports/`

Portanto, o pipeline DEVE passar os caminhos absolutos dos artefatos produzidos no passo
anterior como input do próximo especialista. Eles fazem a leitura via io_agent.read_file,
que aceita qualquer caminho dentro da raiz `adk/`. Especialistas NÃO devem tentar listar
artefatos localmente para descobrir inputs — não vão encontrar, e cairão em Doubt_Artifact
falsamente alegando "input não encontrado".

FLUXO OBRIGATÓRIO (chamadas SEQUENCIAIS — uma tool por turno):

1. DESIGN
   Encaminhe o lote de HUs ao design_architect (inline no request — design_architect
   recebe as HUs direto, não busca em arquivo).
   Aguarde a resposta. **A resposta válida do design_architect é:**
   - "Análise salva em staging: <caminho_absoluto>" (sucesso — capture o caminho e prossiga)
   - "Doubt_Artifact gerado em staging: <caminho_absoluto>" para a HU X (parcial —
     marque a HU como bloqueada, prossiga com as demais)
   - "Erro de persistência: ..." (falha — encerre e reporte o erro)

   NÃO rejeite a resposta do design_architect por estar "sem conteúdo inline" —
   essa é a forma normal de entrega. Se ele retornou um caminho, considere APROVADO.

2. GERAÇÃO DE DIAGRAMAS
   Encaminhe ao mermaid_specialist no request o CAMINHO ABSOLUTO do arquivo de análise
   retornado no passo 1 (ex.: "Gere os diagramas .mmd a partir da análise em
   <caminho_absoluto_da_analise>"). O mermaid_specialist lerá o arquivo via io_agent.read_file.
   Aguarde os caminhos absolutos dos arquivos .mmd persistidos.
   → Se erro de persistência: reporte ao solicitante.

3. GERAÇÃO DE RELATÓRIOS
   Encaminhe ao markdown_specialist no request:
   - O CAMINHO ABSOLUTO do arquivo de análise (do passo 1)
   - O(s) CAMINHO(s) ABSOLUTO(s) do(s) arquivo(s) .mmd (do passo 2)
   Exemplo: "Gere o relatório markdown a partir da análise em <path_analise> e dos
   diagramas em <path_mmd_1>, <path_mmd_2>".
   O markdown_specialist lerá os arquivos via io_agent.read_file.
   Aguarde os caminhos absolutos dos relatórios .md persistidos.
   → Se erro: reporte ao solicitante.

4. VALIDAÇÃO
   Encaminhe ao validator a lista de filenames produzidos.
   Aguarde o veredicto.
   → Se REPROVADO: registre o motivo e prossiga para a entrega final
     com aviso (não tente reciclo automático nesta versão v1).
   → Se APROVADO: prossiga.

5. PERSISTÊNCIA CONFIRMADA
   Os artefatos já foram persistidos pelos passos 1-3. Não chame io_agent
   novamente aqui. Apenas inclua os filenames na entrega final.

REGRAS:
- **Chamadas SEQUENCIAIS — uma sub-tool (AgentTool) por turno.** Nunca emita
  duas tool calls em paralelo neste pipeline.
- Em caso de Doubt_Artifact gerado por qualquer especialista: marque a HU
  afetada como bloqueada e prossiga com as demais. NÃO encerre o pipeline.
- Se um especialista retornar erro/falha textualmente: NÃO RETENTE.
  Registre o erro, prossiga para o próximo passo se possível, ou encerre
  com relatório de erro.
- Idioma: Português brasileiro.

ENTREGA FINAL AO SOLICITANTE (mesmo em caso de falha parcial):
- Lista de arquivos .mmd persistidos em staging com seus caminhos.
- Lista de relatórios .md persistidos em staging com seus caminhos.
- HUs bloqueadas (se houver) com o motivo e caminho do Doubt_Artifact.
- Status final: "concluido", "parcial" ou "falha".
"""

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="design_pipeline",
    description="Pipeline completo de design: transforma HUs em diagramas Mermaid e relatórios Markdown validados e persistidos.",
    instruction=_INSTRUCTION,
    tools=[
        AgentTool(agent=design_architect),
        AgentTool(agent=mermaid_specialist),
        AgentTool(agent=markdown_specialist),
        AgentTool(agent=validator),
        AgentTool(agent=io_agent),
    ],
)