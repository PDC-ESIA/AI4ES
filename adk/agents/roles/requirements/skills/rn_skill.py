from google.adk.skills import models

rn_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="gerar-regra-negocio",
        description="Skill para extrair e documentar Regras de Negócio (RN) baseadas em políticas, cálculos ou restrições lógicas."
    ),
    instructions="""Siga os passos de execução:
PASSO 1: Isolar as restrições de negócio, limites lógicos ou regras de conformidade presentes no contexto.
PASSO 2: Identificar a referência documental ou a origem de cada regra (ex: manual da empresa, legislação, regra de cálculo).
PASSO 3: Formatar a saída rigorosamente com o seguinte template:

TEMPLATE OBRIGATÓRIO:
# Regras de Negócio

| ID       | Descrição                          | Referência / Origem |
|----------|------------------------------------|---------------------|
| RN-[NNN] | [Descrição clara e objetiva da regra] | [Documento/Página/Stakeholder] |
| RN-[NNN] | [Descrição clara e objetiva da regra] | [Documento/Página/Stakeholder] |

---
"""
)