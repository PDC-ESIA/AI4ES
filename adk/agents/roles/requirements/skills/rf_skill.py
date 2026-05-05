from google.adk.skills import models

rf_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="gerar-requisito-funcional",
        description="Skill para estruturar Requisitos Funcionais (RF)."
    ),
    instructions="""Siga os passos de execução:
PASSO 1: Identificar a funcionalidade central e a sua prioridade.
PASSO 2: Mapear as dependências (HU ou UC correspondente).
PASSO 3: Formatar a saída rigorosamente com o seguinte template:

TEMPLATE OBRIGATÓRIO:
# Requisitos Funcionais

| ID       | Descrição                          | Prioridade    | Relacionado a     |
|----------|------------------------------------|---------------|-------------------|
| RF-[NNN] | [O sistema deve...]                | Alta / Média / Baixa          | HU-[NNN] / UC-[NNN]        |"""
)