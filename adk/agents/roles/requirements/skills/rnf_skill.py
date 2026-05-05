from google.adk.skills import models

rnf_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="gerar-requisito-nao-funcional",
        description="Skill para definir Requisitos Não Funcionais (RNF)."
    ),
    instructions="""Siga os passos de execução:
PASSO 1: Identificar a categoria do requisito (Segurança, Desempenho, etc.).
PASSO 2: Definir a restrição e a métrica alvo mensurável.
PASSO 3: Formatar a saída rigorosamente com o seguinte template:

TEMPLATE OBRIGATÓRIO:
# Requisitos Não Funcionais

| ID        | Categoria       | Descrição                  | Métrica / Critério          |
|-----------|-----------------|----------------------------|-----------------------------|
| RNF-[NNN] | [CATEGORIA]     | [O sistema deve...]        | [METRICA_CRITERIO_MENSURAVEL]        |"""
)