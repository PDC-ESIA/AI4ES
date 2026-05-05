from google.adk.skills import models

uc_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="gerar-caso-uso",
        description="Skill para construir Casos de Uso (UC) detalhados."
    ),
    instructions="""Siga os passos de execução:
PASSO 1: Identificar o Ator Principal e as pré-condições necessárias.
PASSO 2: Mapear o Fluxo Principal e os Fluxos Alternativos/Exceção.
PASSO 3: Definir o estado final (Pós-condições).
PASSO 4: Formatar a saída rigorosamente com o seguinte template:

TEMPLATE OBRIGATÓRIO:
# UC-[ID] — [Nome do Caso de Uso]

## Metadados
| Campo         | Valor                        |
|---------------|------------------------------|
| ID            | UC-[número sequencial]       |
| Data geração  | YYYY-MM-DD                   |
| Ator principal| [nome do ator]               |
| HUs relacionadas | HU-[n], HU-[n]            |
| Status        | Rascunho / Revisado / Aprovado |

## Descrição Breve

[Parágrafo de 1-2 frases descrevendo o caso de uso.]

## Atores

- **Primário:** [ator que inicia a interação]
- **Secundário:** [sistemas ou atores de suporte, se houver]

## Pré-condições
- [condição que deve ser verdadeira antes do início]

## Fluxo Principal

1. [passo 1]
2. [passo N]
3. Sistema retorna [resultado].

## Fluxos Alternativos

### FA-[N]: [Nome do fluxo alternativo]
- **Condição:** [quando este fluxo é ativado]
- **Passos:**
  1. [passo alternativo]
  2. [resolução]

## Fluxos de Exceção

### FE-[N]: [Nome da exceção]
- **Condição:** [quando ocorre]
- **Tratamento:** [como o sistema responde]

## Pós-condições
- [estado do sistema após conclusão com sucesso]"""
)