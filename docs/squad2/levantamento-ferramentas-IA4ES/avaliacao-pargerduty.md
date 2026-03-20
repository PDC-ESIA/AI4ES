#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          | PagerDuty                                                                               |
| **Fabricante / Comunidade**     | PagerDuty, Inc.                                                                               |
| **Site oficial / documentação** | https://www.pagerduty.com e https://support.pagerduty.com/                                                                               |
| **Tipo de ferramenta**          | Plataforma SaaS de gestão de incidentes, operações digitais, on‑call management, AIOps e automação de runbooks |
| **Licença / acesso**            | Comercial (modelo SaaS por assinatura, com planos por usuário e add‑ons de AIOps, automação e outros recursos avançados)                                              |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | N/A – a plataforma oferece recursos de AIOps e automação baseados em ML para correlação de eventos, supressão de ruído e priorização de incidentes, não como LLM.                        |
| **Nome do Modelo**                  | N/A (modelos proprietários internos de AIOps/event intelligence, não expostos como “modelo” para o usuário final) |
| **Versão**                          | N/A                                                             |
| **Tamanho (nº de parâmetros)**      | N/A                                                |
| **Acesso**                          | Acesso via plataforma SaaS e APIs REST/integrações; não é oferecido como modelo de IA isolado.                          |
| **Suporte a Fine-tuning**           | Não aplicável para o usuário final (não há fine‑tuning de modelo; há configuração de regras, políticas, filtros e automações).                     |
| **Suporte a RAG**                   | N/A                                                      |
| **Métodos de prompting suportados** | N/A                            |
| **Ferramentas adicionais**          | Integrações com ferramentas de observabilidade e colaboração (Slack, MS Teams, Jira, Datadog, AWS, etc.) e módulos de automação/process automation.    |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Cloud (SaaS). A solução é executada na nuvem do PagerDuty; o cliente acessa via web, apps móveis e APIs.                 |
| **Infraestrutura utilizada no teste** | Não aplicável no cliente (infra gerenciada pelo fornecedor). Do lado do cliente, basta acesso web/API e integrações com ferramentas de monitoramento/colaboração.    |
| **Custos (quando aplicável)**         | Assinatura por usuário/mês com planos Business/Enterprise e add‑ons (AIOps, automação, status pages etc.)|

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              | Parcialmente                      | Pode apoiar elicitação de requisitos operacionais ao registrar incidentes recorrentes, SLAs violados e gargalos, que viram insumo para novos requisitos.                         |
| Análise                 | Parcialmente                      | Dashboards e relatórios (MTTR, frequência de incidentes) ajudam a analisar requisitos de confiabilidade e disponibilidade. |
| Priorização             | Parcialmente                      | Priorização de incidentes por severidade/impacto, que influencia priorização de requisitos de correção e melhorias. |
| Modelagem               | N/A                      | Não oferece modelagem de requisitos (diagramas, casos de uso etc.).                         |
| Validação / Verificação | Parcialmente                      | Indicadores de estabilidade e redução de incidentes podem ser usados para validar requisitos não funcionais de disponibilidade/tempo de resposta. |
| Documentação            | Parcialmente                      | Post‑incident reviews e timelines documentam problemas e decisões, servindo como documentação de requisitos e seus ajustes.                         |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | N/A                   | Não gera arquitetura de software de aplicações.                         |
| Decisões arquiteturais           | Parcialmente          | Dados de incidentes por serviço/componente apoiam decisões arquiteturais (refatorar, segmentar serviços, rever dependências críticas).                          |
| Avaliação de trade-offs          | Parcialmente          | Métricas de disponibilidade e impacto podem ser usadas para avaliar trade‑offs entre complexidade, resiliência e custo operacional.                          |
| Uso de padrões arquiteturais     | N/A                   | Não sugere padrões arquiteturais, mas incentiva práticas de arquitetura resiliente (observabilidade, separação de serviços críticos).                         |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | N/A                   | Não atua em design ou padrões de projeto                         |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | N/A                   | Não gera código de aplicação.                         |
| Refatoração       | N/A                   | Não refatora código, mas dados de incidentes podem motivar refatorações em serviços problemáticos.                          |
| Detecção de bugs  | Parcialmente          | Não é ferramenta de teste estático, mas recebe alertas de erros em produção (ex.: via APM/logs) e centraliza incidentes. |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | N/A                   | Não gera casos de teste.                         |
| Execução de testes automatizados                 | Parcialmente          | Pode ser integrado a pipelines de CI/CD para criar incidentes a partir de falhas em testes ou deploys.                         |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Parcialmente          | Integra com pipelines (ex.: via webhooks/APIs) para abrir incidentes quando builds/deploys falham ou causam degradação de serviço.                         |
| Automação                         | Suporta               | Runbook Automation e Automation Actions executam scripts de diagnóstico/correção automática, inclusive via Slack/Teams.                         |
| Monitoramento                     | Suporta               | Não monitora por si só, mas centraliza alertas de mais de 600 ferramentas de monitoramento/APM/logs, agregando e correlacionando eventos.                         |
| Documentação técnica automatizada | Suporta               | Gera timelines, registros de incidentes e post‑incident reviews com dados consolidados, úteis como documentação operacional.                         |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | Suporta               | Pode disparar automações de correção (reinício de serviços, rollback, scripts de remediação) para incidentes recorrentes.                         |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | Parcialmente          | Métricas de incidentes e disponibilidade informam planejamento de melhorias e dívidas técnicas em projetos. |
| Execução                            | Parcialmente          | Coordena resposta a incidentes, o que impacta execução de sprints e releases em times DevOps/SRE.                         |
| Controle                            | Parcialmente          | Dashboards (MTTR, número de incidentes, SLAs) suportam controle de metas operacionais ligadas a projetos.                        |
| Encerramento                        | Parcialmente          | Post‑incident reviews funcionam como encerramento formal de incidentes e ações corretivas associadas a projetos.                          |
| Gestão de riscos                    | Suporta               | Alertas proativos, severidade, SLAs e automação reduzem risco operacional e ajudam a identificar pontos críticos.                          |
| Estimativas (tempo, custo, esforço) | Parcialmente          | Histórico de incidentes e MTTR pode ser usado para estimar esforço de estabilização e capacidade da operação.                         |
| Medição                             | Suporta               | Fornece métricas detalhadas sobre incidentes, disponibilidade, tempo de resposta e resolução, apoiando medições contínuas.                         |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐             | Alta precisão em alertas e roteamento quando integrações e regras estão bem configuradas; depende da qualidade dos sinais de monitoramento.            |
| Profundidade técnica                | ⭐⭐⭐⭐             | Oferece recursos avançados de incident management, AIOps e automação; profundidade técnica alta para contexto de operações/SRE.            |
| Contextualização no código/problema | ⭐⭐⭐⭐             | Conecta incidentes a serviços, componentes e ferramentas (APM, logs), oferecendo bom contexto técnico para troubleshooting.            |
| Clareza                             | ⭐⭐⭐⭐             | Interfaces de incident timeline, roles & tasks e status pages facilitam entendimento de causa e impacto. |
| Aderência às melhores práticas      | ⭐⭐⭐⭐             | Encoraja práticas DevOps/SRE: on‑call, postmortems, automação, SLIs/SLOs e colaboração em tempo real.            |
| Consistência entre respostas        | ⭐⭐⭐⭐             | Com configurações estáveis, comporta‑se de forma consistente em correlação, escalonamentos e fluxos.            |
| Ocorrência de alucinações           | Baixa                  | Não é LLM; “erros” decorrem de má configuração/integrations, não de alucinação de conteúdo.             |

---

#  **6. Experimentos Realizados**

* Software em produção necessário para realizar experimentos

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**
* Automação de alertas, escalonamentos e runbooks, reduzindo esforço manual e MTTR.
* Integrações extensas com ferramentas de monitoramento, nuvem e colaboração (mais de centenas de integrações).
* Gestão de on‑call madura, com escalas flexíveis, notificações multicanal e relatórios.
* Suporte forte a práticas SRE: incident lifecycle, post‑incident reviews, métricas operacionais.

### **Limitações**
* Custo elevado em cenários com muitos usuários e necessidade de vários add‑ons (AIOps, automação, status page).
* Curva de configuração inicial relativamente alta (serviços, integrações, políticas de escalonamento e regras de roteamento).
* Não substitui ferramentas de monitoramento/APM; depende de boa instrumentação externa.
​

---

#  **8. Riscos, Custos e Considerações de Uso**

* Dependência de vendor: forte dependência do SaaS do PagerDuty para gestão de incidentes e plantões.
* Custos recorrentes: modelo por usuário + add‑ons pode escalar rapidamente com o crescimento da equipe.​
* Limitações em privacidade/compliance: dados de incidentes e integrações ficam na nuvem do fornecedor, exigindo avaliação de requisitos regulatórios.
* Barreiras técnicas de adoção: necessidade de integrar múltiplas fontes de monitoramento e ajustar regras para evitar ruído.
* Dificuldades de execução local: não há versão on‑premise completa; foco é SaaS.


---

#  **9. Conclusão Geral da Análise**
* A ferramenta é adequada principalmente para operações de software, SRE e DevOps: gestão de incidentes, on‑call, automação e monitoramento integrado.
* Deve ser evitada como solução principal para desenvolvimento, testes e design de software, pois não fornece recursos de IDE, geração de código ou testes automatizados.
* A maturidade técnica é alta, sendo uma solução consolidada de mercado para operações digitais de missão crítica.
* Vale a pena para organizações com ambiente distribuído, alta criticidade de disponibilidade e times dedicados a SRE/DevOps; pode ser pesada/cara para equipes pequenas com requisitos simples.


---

#  **10. Referências e Links Consultados**

* Site oficial do PagerDuty (Incident Management, On‑Call Management, automação).
* Artigos explicando recursos e benefícios do PagerDuty em gestão de incidentes.
* Informações de preços e modelo de licenciamento SaaS.