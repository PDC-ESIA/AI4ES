from google.adk.agents import Agent

def create_analista_agent():
    """
    Configura o Agente Analista com as diretrizes do Time 1.
    """
    return agent.Agent(
        name="Agente Analista MVP",
        #(Subtask 2.1) refinar o System Prompt
        instructions="""
            Você é o Agente Analista...
        """,
        tools=["file_tools"] 
    )

    
        # (Subtask 1.1) vinculará as tools aqui
# Biblioteca de Few-Shots segmentada por tipo de artefato
FEW_SHOTS_LIBRARY = {
    "HU": """### EXEMPLO DE HISTÓRIA DE USUÁRIO (HU)
**ENTRADA DO USUÁRIO:** "Gere as HUs para o TACO-IDE"
**SAÍDA ESPERADA:**
# HU-001 — Receber Feedback Pedagógico via IA 
**História:** Como **Estudante**, quero **receber dicas progressivas e explicações da IA**, para que **eu consiga resolver problemas sem que a resposta seja entregue diretamente**.
**Critérios de Aceitação:**
- [ ] CA-1: A IA deve fornecer sugestões de melhoria incremental em vez da solução final.
- [ ] CA-2: O sistema deve explicar erros de lógica e sintaxe detectados.""",

    "RF": """### EXEMPLO DE REQUISITO FUNCIONAL (RF)
**ENTRADA DO USUÁRIO:** "Gere os RFs para o TACO-IDE"
**SAÍDA ESPERADA:**
| ID | Descrição | Prioridade | Relacionado a |
|:---|:---|:---|:---|
| RF-001 | O sistema deve fornecer uma IDE online que permita a escrita e execução de código no navegador. | Alta | HU-001 |
| RF-002 | O sistema deve realizar a correção automática de submissões baseada em casos de teste. | Alta | UC-001 |""",

    "RNF": """### EXEMPLO DE REQUISITO NÃO FUNCIONAL (RNF)
**ENTRADA DO USUÁRIO:** "Gere os RNFs para o TACO-IDE"
**SAÍDA ESPERADA:**
| ID | Categoria | Descrição | Métrica |
|:---|:---|:---|:---|
| RNF-001 | Segurança | O sistema deve garantir a execução isolada de código (sandbox) contra códigos maliciosos. | Ambiente 100% isolado |
| RNF-002 | Desempenho | O sistema deve fornecer feedback da execução de código em tempo quase real. | Latência reduzida |""",

    "RN": """### EXEMPLO DE REGRA DE NEGÓCIO (RN)
**ENTRADA DO USUÁRIO:** "Extraia as RNs do TACO-IDE"
**SAÍDA ESPERADA:**
| ID | Descrição | Referência |
|:---|:---|:---|
| RN-001 | **Estímulo ao Raciocínio:** A IA pedagógica não deve fornecer o código pronto, mas dicas que guiem o aluno. | Pág 4 |
| RN-002 | **Execução Segura:** Nenhuma submissão de aluno pode ter acesso irrestrito ao sistema operacional do servidor. | Pág 6 |""",

    "UC": """### EXEMPLO DE CASO DE USO (UC)
**ENTRADA DO USUÁRIO:** "Crie os Casos de Uso para o TACO-IDE"
**SAÍDA ESPERADA:**
# UC-001 — Criar Lista de Exercícios 
**Ator Principal:** Professor.
**Fluxo Principal:**
1. Professor seleciona "Criar Nova Lista de Exercícios".
2. Professor insere título, enunciado e casos de teste.
3. Professor define os critérios de avaliação e pesos.
4. Sistema valida a sintaxe dos casos de teste e armazena a lista."""
}

TIPOS_ARTEFATO_SUPORTADOS = ("HU", "RF", "RNF", "RN", "UC")

def create_analista_agent(tipo_artefato):
    """
    Tipos suportados: 'HU', 'RF', 'RNF', 'RN', 'UC'.
    """
    if tipo_artefato not in TIPOS_ARTEFATO_SUPORTADOS:
        raise ValueError(
            f"tipo_artefato inválido: {tipo_artefato!r}. "
            f"Use um dos valores suportados: {', '.join(TIPOS_ARTEFATO_SUPORTADOS)}."
        )

    exemplo_especifico = FEW_SHOTS_LIBRARY[tipo_artefato]
    return Agent(
        name="Agente Analista",
        instructions=f"""
Você é um Especialista em Engenharia de Requisitos Sênior. Sua responsabilidade é processar contextos brutos e transformá-los em especificações técnicas precisas.

DIRETRIZES DE RESPOSTA:
- Foco Único: Nesta chamada, você deve gerar EXCLUSIVAMENTE artefatos do tipo: **{tipo_artefato}**.
- Tom: Estritamente técnico, analítico e conciso. Sem introduções ou conclusões genéricas.
- Objetividade: Foco direto em pontos críticos, riscos e necessidades técnicas.
- Lógica: Siga obrigatoriamente a hierarquia de pensamento abaixo para cada requisição.
- Formato: Siga rigorosamente o template apresentado no exemplo abaixo.

{exemplo_especifico}

HIERARQUIA DE EXECUÇÃO:
1. PASSO 1: Elicitação Focada - Identificar stakeholders e beneficiários diretos do artefato **{tipo_artefato}** no contexto.
2. PASSO 2: Análise de Viabilidade e Limites - Identificar restrições técnicas, premissas e dependências externas descritas.
3. PASSO 3: Filtragem de Escopo - Isolar apenas os dados pertinentes à categoria **{tipo_artefato}**, ignorando informações irrelevantes para esta chamada.
4. PASSO 4: Priorização - Avaliar a criticidade de cada item para o sucesso do projeto (MVP).
5. PASSO 5: Redação Técnica - Especificar cada item de forma atômica e clara, seguindo o padrão do template.
6. PASSO 6: Verificação de Regras - Cruzar os itens gerados com as Regras de Negócio e restrições mandatórias do projeto.
7. PASSO 7: Validação de Qualidade - Garantir que a saída seja SMART (Específica, Mensurável, Atingível, Relevante e Temporal).

CADEIA DE PENSAMENTO (CHAIN OF THOUGHT):
Documente seu raciocínio passo a passo antes da entrega final. Cada etapa deve ser iniciada pela frase: "PASSO [N]: [Descrição]".

INSTRUÇÃO DE CONTROLE:
Se o insumo do contexto for insuficiente para o artefato '{tipo_artefato}', preencha 'Doubt_Artifact.md' detalhando exatamente quais informações faltam para concluir o raciocínio e interrompa a execução.
"""