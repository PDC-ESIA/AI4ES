#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          | mabl                                                                                |
| **Fabricante / Comunidade**     | mabl Inc.                                                                               |
| **Site oficial / documentação** | https://www.mabl.com/ e  [Documentação](https://help.mabl.com/hc/en-us)                                                                              |
| **Tipo de ferramenta**          | Plataforma de Automação de Testes Inteligente (Enterprise SaaS / Low-code) |
| **Licença / acesso**            | Comercial (Plano Gratuito de teste por 14 dias).                                            |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | LLM / multimodal / difusão / híbrido                         |
| **Nome do Modelo**                  | Não divulgado (proprietário) |
| **Versão**                          |                                                              |
| **Tamanho (nº de parâmetros)**      | Se disponível                                                |
| **Acesso**                          | API comercial / Open-source / Local                          |
| **Suporte a Fine-tuning**           | Não aplicável                     |
| **Suporte a RAG**                   | Sim. Integração com documentação de requisitos (PDF, Jira) e análise em tempo real do DOM da página.                                                      |
| **Métodos de prompting suportados** | Prompting em linguagem natural orientado a objetivos de teste                            |
| **Ferramentas adicionais**          | mabl Trainer: Extensão/App para gravação assistida. mabl CLI: Execução e integração local. |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Criação: Local (mabl Desktop App - Windows/macOS). Execução: Cloud (Nuvem mabl em múltiplos browsers).                |
| **Infraestrutura utilizada no teste** | Nuvem mabl com execução via mabl Desktop e integração com Google Chrome.    |
| **Custos (quando aplicável)**         | N/A |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              |         N/A           |                          |
| Análise                 |         N/A           |                          |
| Priorização             |         N/A           |                          |
| Modelagem               |         N/A           |                          |
| Validação / Verificação |         N/A           |                          |
| Documentação            |         N/A           |                          |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais |         N/A           | Fora do escopo da ferramenta.                         |
| Decisões arquiteturais           |         N/A           | Não atua em decisões de arquitetura de sistemas.                         |
| Avaliação de trade-offs          |         N/A           | Não compara alternativas arquiteturais.                         |
| Uso de padrões arquiteturais     |         N/A           | O foco do mabl é validação de comportamento externo (black-box).                         |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto |         N/A           |                          |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código |         N/A           |                          |
| Refatoração       |         N/A           |                          |
| Detecção de bugs  | Parcial                       | O que faz: Detecta falhas funcionais e visuais. <br> Exemplo: Falha ao não encontrar elemento esperado ou divergência visual após mudança inesperada. <br> Limitação: Não identifica causa raiz no código.                          |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | Sim                   | O que faz: Gera testes E2E (End-to-end) a partir de linguagem natural. <br> Como faz: Interpreta objetivos e constrói fluxos completos de interação. <br> Exemplo: Geração automática de um teste para preenchimento completo do formulário em demoqa.com.                         |
| Execução de testes automatizados                 | Sim                   | O que faz: Executa testes end-to-end automaticamente, simulando fluxos completos de uso da aplicação em navegadores reais. <br> Como faz: suporte a disparo manual, agendamento ou integração com pipelines de CI/CD.                        |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Sim                   | Integração com GitHub Actions, GitLab CI, Jenkins, etc.                         |
| Automação                         | Sim                   | Automação completa do ciclo de testes E2E e planos de teste.                         |
| Monitoramento                     | Parcial               | Dashboards de execução, falhas e cobertura.                         |
| Documentação técnica automatizada | Não                   | Testes funcionam como documentação viva, mas não há geração formal de docs.                          |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | Parcial               | Self-healing de seletores. Não corrige lógica da aplicação. <br> Testes se adaptam a pequenas mudanças sem regravação manual.                          |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        |        N/A            |                          |
| Execução                            | Sim                   | Referente à implementação de testes.                         |
| Controle                            |        N/A            |                          |
| Encerramento                        |        N/A            |                          |
| Gestão de riscos                    |        N/A            |                          |
| Estimativas (tempo, custo, esforço) |        N/A            |                          |
| Medição                             |        N/A            |                          |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐⭐            | Demonstrou alta precisão na compreensão do objetivo do teste e na identificação dos componentes da aplicação testada. As validações foram corretamente inferidas a partir do comportamento real da interface, sem depender de suposições ou regras genéricas, o que reduziu a ocorrência de falsos positivos durante a execução do teste.              |
| Profundidade técnica                | ⭐⭐⭐⭐⭐            | Demonstra compreensão consistente dos diferentes níveis de teste (interface, API e aplicação), aplicando validações adequadas a cada camada. A análise considera tanto regras de negócio informadas quanto comportamentos técnicos, como validações de dados, fluxos e respostas do sistema.             |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            | As decisões de teste são alinhadas ao contexto do sistema avaliado, levando em conta o domínio do problema, os dados manipulados e as restrições existentes. Os cenários propostos refletem situações reais de uso, independentemente da tecnologia ou camada testada.            |
| Clareza                             | ⭐⭐⭐⭐⭐            | O diálogo durante a execução do teste foi claro e proativo, especialmente ao sinalizar impedimentos técnicos, como limitações na identificação de elementos ou dependências de carregamento da página. As mensagens geradas facilitaram o entendimento do que estava sendo testado e do motivo de eventuais falhas.             |
| Aderência às melhores práticas      | ⭐⭐⭐⭐⭐            | Apresenta decisões compatíveis com práticas consolidadas de testes automatizados, favorecendo manutenibilidade e reduzindo acoplamento a detalhes específicos da implementação.             |
| Consistência entre respostas        | ⭐⭐⭐⭐⭐            | Mantém coerência técnica e conceitual ao longo da interação, apresentando respostas alinhadas entre si e compatíveis com os objetivos do teste. As recomendações e ajustes propostos não entram em conflito e evoluem de forma lógica conforme novas informações surgem.             |
| Ocorrência de alucinações           | Baixa |             | Não foram observados comportamentos típicos de alucinação. As validações realizadas foram consistentes com as restrições efetivamente impostas pela aplicação alvo, indicando que a IA se baseou no estado real da interface e nas respostas do sistema, e não em inferências especulativas. |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

**1. Teste 1: Formulário WebTables (demoqa.com)**
**Objetivo:** Testar geração via linguagem natural e adaptação a validações reais

**Prompt:**
> "Preencha first name, last name e email, clique em submit. 
> O teste deve passar, caso ele falhe pela falta de preencher demais campos."

**Resultado:**
- Mabl gerou task plan estruturado
- Detectou que Age, Salary, Department eram obrigatórios
- Pausou e ofereceu 2 alternativas (preencher os campos ou atualizar objetivo do teste)
- Após escolha, preencheu campos e validou inserção correta.

**Conclusão:** 
Mabl demonstrou IA generativa com raciocínio crítico, 
não apenas automação de UI tradicional.

**2. Teste 2: API de Criação de Usuário (REST – ambiente de demonstração)**
Objetivo: Avaliar a geração de testes de API a partir de linguagem natural e a adaptação a respostas reais do endpoint

Prompt:

> Envie uma requisição POST para criar um usuário com dados fictícios.
> O teste deve passar apenas se a API retornar status 201 e o campo id estiver presente na resposta.

**Resultado:**

- Mabl identificou automaticamente o método HTTP, o endpoint e o formato JSON esperado
- Gerou a requisição com payload fictício consistente (nome, email e senha)
- Executou a chamada e validou o status HTTP retornado
- Validou a presença e o tipo do campo id na resposta da API

Conclusão:
O mabl demonstrou capacidade de aplicar raciocínio sobre contratos de API e critérios de sucesso, indo além da simples execução de requisições e validando semanticamente a resposta do serviço.


### ● Resultados quantitativos

* Produtividade: Redução do tempo de criação de ~20 minutos (manual) para <3 minutos (IA Agêntica).
* Assertividade: O agente de IA interrompeu o fluxo e solicitou assistência humana ao identificar uma contradição lógica.


### ● Exemplos (copie trechos de código, respostas etc.)

---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Geração de testes via IA (diferencial crítico)
   - Reduz o tempo de criação de testes
   - Não requer conhecimento técnico avançado de Selenium/XPath
     
* Raciocínio crítico e detecção de conflitos
   - Identifica contradições entre prompt e realidade
   - Não falha silenciosamente
 
* Adaptação dinâmica
   - Consulta usuário quando há ambiguidade
   - Oferece soluções contextualizadas

* Resiliência: Redução drástica da manutenção de testes através do Auto-healing
   
* Interface intuitiva
   - Feedback claro durante execução
   - Task plan estruturado facilita debug

### **Limitações**

* Dependência de SaaS: Não é possível utilizar as capacidades de IA sem conexão cloud.

---

#  **8. Riscos, Custos e Considerações de Uso**

* Dependência de vendor: os testes criados no mabl são proprietários e residem na infraestrutura da plataforma.
* Custos recorrentes: a ferramenta utiliza um modelo SaaS (Software as a Service) com faturamento recorrente baseado em licenças ou volume de execuções ("créditos")
* Limitações em privacidade ou compliance: como uma ferramenta baseada em nuvem, o mabl processa e armazena metadados da aplicação, screenshots e o DOM das páginas em seus servidores.
* Barreiras técnicas de adoção: embora a curva de aprendizado inicial seja baixa, o domínio de cenários complexos (como condicionais avançados e integração de APIs) exige treinamento nas funcionalidades específicas da plataforma.
* Dificuldades de execução local: nativamente otimizado para execução na nuvem.

---

#  **9. Conclusão Geral da Análise**

* A ferramenta é adequada para quais atividades de ES?

  O mabl é altamente eficaz nas atividades de Teste de Software (SWEBOK 4.5) e Manutenção de Software (4.7). Ele se destaca especificamente em:
    - Automação de Testes Funcionais e de Regressão: Ideal para fluxos de ponta a ponta (E2E) em interfaces web, APIs e mobile.
    - Apoio à Análise de Verificação: Através da IA agêntica, auxilia na identificação de conflitos entre instruções de teste e restrições reais da interface.
    - Redução de Débito Técnico de QA: O recurso de Auto-healing minimiza o esforço de manutenção de suítes de teste em aplicações com mudanças frequentes de UI.
  
* Em quais casos deve ser evitada?
  
  - Projetos que exigem execução local estrita sem acesso à nuvem, devido à dependência do motor de IA baseado em SaaS;
  - Projetos com restrições rigorosas de privacidade.
  
* Em qual maturidade técnica ela se encontra?
  
  O mabl pode ser classificado como uma solução consolidada e estável, com recursos avançados de automação apoiados por IA, mas ainda limitada em extensibilidade e personalização profunda quando comparada a frameworks tradicionais.

* Vale a pena para a organização?
  
  Para aquelas que priorizam produtividade, redução de esforço operacional e escalabilidade dos testes, especialmente em ambientes corporativos e equipes distribuídas. Necessário avaliar custos.
---

#  **10. Referências e Links Consultados**

  * [mabl](https://www.mabl.com/platform)
  * [Agentic Testing](https://www.mabl.com/agentic-testing-for-software-development-mabl)
  * [AI App Testing](https://www.mabl.com/ja/ai-application-testing)
  * [AI-Native Test Automation](https://www.mabl.com/ai-test-automation)
  * [AI Auto-Healing](https://www.mabl.com/auto-healing-tests)
