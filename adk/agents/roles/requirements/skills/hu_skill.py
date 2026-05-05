from google.adk.skills import models

hu_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="gerar-historia-usuario",
        description="Skill para elicitar e formatar Histórias de Usuário (HU) seguindo o template oficial."
    ),
    instructions="""Siga os passos de execução:
PASSO 1: Identificar ator principal, necessidade e valor.
PASSO 2: Redigir a história no formato padrão.
PASSO 3: Definir Critérios de Aceitação atómicos.
PASSO 4: Formatar a saída rigorosamente com o seguinte template:

TEMPLATE OBRIGATÓRIO:
# HU-[ID] — [Título Curto]

## Metadados
| Campo         | Valor                        |
|---------------|------------------------------|
| ID            | HU-[NNN]       |
| Data geração  | DD-MM-YYYY                  |
| Origem        | [trecho ou seção do contexto]|
| Versão        | [versão] |
| Status        | Rascunho / Revisado / Aprovado |
| Prioridade    | Alta / Média / Baixa |

## História

> Como **[Persona/Papel]**,  
> quero **[Ação/Funcionalidade]**,  
> para que **[Benefício ou objetivo]**.

## Critérios de Aceitação

- [ ] CA-[N]: [descrição do critério]"""
)