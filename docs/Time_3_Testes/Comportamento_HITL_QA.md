# Documentação de Comportamento: HITL Gate no Agente QA

> **Classificação da Análise:** Requisito Arquitetural Core (Não é um bug)
> **Subagente Afetado:** `action_planner` (Agente QA)
> **Componentes Envolvidos:** `hitl_tool.py`, `Protocolo-Supervisor-QA.md`, Google ADK

---

## 1. Visão Geral

O comportamento de pausar a execução e não devolver uma resposta imediata no `action_planner` é intencional e essencial para a integridade do sistema. O protocolo oficial determina explicitamente a obrigatoriedade da intervenção humana ao encontrar inconsistências, ambiguidades ou bloqueios lógicos (frequentemente materializados através dos *Doubt Artifacts*). 

Este gate atua como uma barreira de segurança para evitar que o LLM tome decisões não supervisionadas sobre requisitos incompletos.

---

## 2. Mecânica de Funcionamento no ADK

A interrupção do fluxo baseia-se no comportamento nativo de ferramentas de longa duração (Long-Running Tools) no framework subjacente:

* **Acionamento:** Quando o agente invoca as ferramentas `create_hitl_checkpoint` ou `aguardar_aprovacao_humana` (presentes em `adk/src/agents/qa_agent/tools/hitl_tool.py`).
* **Sinalização de Pausa:** A ferramenta retorna propositalmente `None`. Em uma `LongRunningFunctionTool`, retornar `None` avisa ao motor do Google ADK que a ferramenta não possui uma auto-resposta imediata.
* **Suspensão do Ciclo ReAct:** Ao receber este sinal, o motor entende isso como uma suspensão do ciclo ReAct (Reasoning and Acting). O orquestrador detecta essa pendência através do monitoramento de `Event.long_running_tool_ids` e emite um evento bloqueante aguardando injeção externa.
* **Status do Sistema:** O ciclo de pensamento do LLM é interrompido (*yield*/*pause*). Durante este estado, nenhuma chamada subsequente (como execuções do `pytest` ou geração de código) ocorrerá.

---

## 3. Fluxo de Intervenção e Resolução

Para que o agente retome sua operação, é necessária a ação direta de um operador ou supervisor humano:

1. **Notificação:** O sistema emite o alerta/Doubt Artifact indicando o motivo da pausa.
2. **Avaliação Humana:** O supervisor do fluxo (ou o usuário via interface) analisa o estado atual e as dúvidas levantadas pelo agente.
3. **Injeção de Resposta (`function_response`):** O operador deve resgatar a execução devolvendo uma string de decisão padronizada. As decisões mapeadas incluem:
   * `"aprovar"`
   * `"rejeitar"`
   * `"solicitar_ajustes"`
   *(acompanhadas de feedback detalhado, se necessário)*.
4. **Retomada:** O sistema injeta essa resposta no evento bloqueado. O agente QA "acorda" da suspensão, recebe o feedback humano como resultado da tool, e segue a rota condicional estipulada pela sua lógica interna.

---

## 4. Justificativa e Regras de Manutenção

### Por que não contornar este bloqueio?
A natureza deste bloqueio é uma *Feature Core* implementada para garantir o estrito cumprimento do **Protocolo do Supervisor de QA**. Remover este gate ou automatizá-lo com respostas simuladas resultaria em:

* **Alucinações Não Detectadas:** O LLM poderia assumir falsas premissas de regras de negócio na ausência de esclarecimento, gerando suítes de testes que passam, mas validam comportamentos incorretos.
* **Quebra de Compliance:** Permitir que o agente defina fluxos de teste sem o "de acordo" humano em cenários dúbios viola as diretrizes de QA do projeto.