# Agente Requirements
**Time:** Codificação   
**Branch:** feature/140-optimizer-requirements  
**Modelo:** github_copilot/gpt-4 (padrão) — sobrescreva com `ADK_LLM_MODEL`

---

## O que este agente faz

Recebe pedidos de desenvolvimento ou PRDs brutos e os transforma em requisitos
funcionais atômicos, verificáveis e estruturados para consumo pelo agente de
codificção do pipeline.

O agente NÃO implementa código. NÃO sugere arquitetura. Apenas analisa e estrutura requisitos.

---

## Estrutura de arquivos

```
agents/roles/requirements/
├── __init__.py
├── agent.py                  
├── prompt.py                 
├── schemas.py                
├── tools_requirements.py     — tools: leitura de PRD e Doubt Artifact
└── README.md
```

---

## Tipos de entrada suportados

**Tipo 1 — Pedido direto no terminal do ADK:**
```
crie uma página HTML com o conteúdo Hello World
altere o conteúdo da página para Hello Brasil
implemente uma função Python que ordena uma lista
```

**Tipo 2 — PRD bruto como texto no prompt:**
```
Módulo: Autenticação
O sistema deve suportar login via e-mail e senha.
Deve gerar token JWT com expiração de 8 horas.
...
```

**Tipo 3 — PRD bruto como arquivo:**
```
Analise o PRD em: /caminho/absoluto/para/arquivo.md
```
IMPORTANTE: Para enviar um PRD como arquivo, informe o caminho
absoluto diretamente no texto. O upload pela Dev UI
não aciona a tool de leitura de arquivo.

Exemplo correto:
Analise o PRD em: C:\caminho\absoluto\para\arquivo.md

Não use o botao de upload da Dev UI para PRDs.
---

## Saída esperada

O agente sempre retorna JSON estruturado no seguinte formato:

```json
{
  "requirements": [
    {
      "id": "REQ-001",
      "description": "Criar arquivo index.html com conteúdo Hello World",
      "acceptance_criteria": "Arquivo existe e exibe Hello World no navegador"
    },
    {
      "id": "REQ-002",
      "description": "...",
      "acceptance_criteria": "..."
    }
  ]
}
```

---

## Tools disponíveis

| Tool | Quando é chamada |
|------|-----------------|
| `tool_ler_prd_arquivo` | A entrada é um caminho de arquivo .md ou .txt |
| `tool_gerar_doubt_artifact` | A entrada é ambígua ou contraditória |

---

## Protocolo de Doubt Artifact

Quando o agente detecta ambiguidade ou contradição na entrada, ele gera
automaticamente o arquivo `Doubt_Artifact_requirements.md` e pausa a execução.

Exemplo de entrada que dispara o Doubt Artifact:
```
altere o sistema para funcionar melhor e ser mais rápido
```

O arquivo gerado fica na raiz de `adk/` para análise.

---

## Como testar localmente

### 1. Cenários de teste sugeridos

**Cenário 1 — Pedido simples (deve retornar JSON com requisitos):**
```
crie uma página HTML com o conteúdo Hello World
```

**Cenário 2 — Entrada ambígua (deve gerar Doubt Artifact):**
```
altere o sistema para funcionar melhor e ser mais rápido
```

**Cenario 3 — PRD com multiplos requisitos:**
```
Módulo: Autenticação de Usuários
O sistema deve suportar dois perfis: Aluno e Professor.
Login via e-mail e senha com token JWT de 8 horas.
Bloqueio após 5 tentativas falhas consecutivas por 15 minutos.
Professores podem criar turmas e visualizar relatórios.
```

---

## Decisões técnicas

**Por que output_schema + tools juntos?**
As tools deste agente (`tool_ler_prd_arquivo` e `tool_gerar_doubt_artifact`) são de suporte ao
processamento — não de geração de saída — portanto não conflitam com o schema.

**Por que apenas 2 tools?**
As tools de salvar Context Windows em JSON e Markdown foram removidas pois
a saída estruturada agora é entregue diretamente via `output_schema`,
consumida pelo próximo agente no pipeline sem necessidade de arquivos intermediários.

**Schema adotado:**
O schema segue exatamente o padrao definido garantindo compatibilidade com os demais agentes do pipeline.

