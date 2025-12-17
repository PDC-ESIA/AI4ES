#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          | Amazon Q Developer                                                             |
| **Fabricante / Comunidade**     | AWS (Amazon Web Services)                                                      |
| **Site oficial / documentação** | https://aws.amazon.com/pt/q/developer/                                         |
| **Tipo de ferramenta**          | Assistente de código e engenharia de software integrado a IDE e Cloud          |
| **Licença / acesso**            | Comercial (SaaS), com camada gratuita e plano Pro                              |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                                  |
| ----------------------------------- | -------------------------------------------------------------------------- |
| **Tipo de IA Generativa**           | LLM Multimodal (Código e Texto)                                            |
| **Nome do Modelo**                  | Orquestração via Amazon Bedrock (Titan + Claude ajustados) / Sem nome único|
| **Versão**                          | Proprietária (não divulgada)                                               |
| **Tamanho (nº de parâmetros)**      | Não divulgado                                                              |
| **Acesso**                          | API e interface SaaS                                                       |
| **Suporte a Fine-tuning**           | Sim (fine-tuning proprietário da AWS)                                      |
| **Suporte a RAG**                   | Sim (fortemente utilizado)                                                 |
| **Métodos de prompting suportados** | Chain-of-Thought (implícito), ReAct, multi-agent                           |
| **Ferramentas adicionais**          | AWS Bedrock, IDEs (VS Code, JetBrains), CodeCatalyst, Eclipse              |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                                       |
| ------------------------------------- | ------------------------------------------------|
| **Onde roda?**                        | Cloud (AWS)                                     |
| **Infraestrutura utilizada no teste** | Chips AWS Trainium e Inferentia                 |
| **Custos (quando aplicável)**         | Gratuito limitado; Pro ~ US$ 19/mês por usuário |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

Para cada item abaixo, descreva:

* **O que a ferramenta faz**
* **Como faz**
* **Exemplos / evidências**
* **Limitações observadas**

Use N/A quando não aplicável.

---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações                              |
| ----------------------- | --------------------- | ----------------------------------------------------- |
| Elicitação              | Parcial               | Interpreta issues do Jira e documentos do CodeCatalyst|
| Análise                 | Sim                   | Analisa requisitos e sugere planos de implementação   |
| Priorização             | Parcial               | Auxilia indiretamente via análise de impacto          |
| Modelagem               | N/A                   | Não gera modelos formais                              |
| Validação / Verificação | Parcial               | Validação conceitual via checklist                    |
| Documentação            | Sim                   |  Geração automática de documentação técnica           |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações                      |
| -------------------------------- | --------------------- | --------------------------------------------- |
| Geração de designs arquiteturais | Sim                   | Sugestões baseadas no AWS Well-Architected    |
| Decisões arquiteturais           | Sim                   | Comparação Lambda vs EC2, custo x performance |
| Avaliação de trade-offs          | Sim                   | Orientada por boas práticas AWS               |
| Uso de padrões arquiteturais     | Sim                   | Microserviços, serverless, event-driven       |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações           |
| ---------------------------------- | --------------------- | ---------------------------------- |
| Sugestão/uso de padrões de projeto |  Parcial              | Sugestões implícitas via código    |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações                    |
| ----------------- | --------------------- | ------------------------------------------- |
| Geração de código | Sim                   | Autocomplete e geração de funções completas |
| Refatoração       | Sim                   | Atualização automática (ex: Java 8 → 17)    |
| Detecção de bugs  | Sim                   | Varredura de segurança integrada            |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações     |
| ------------------------------------------------ | --------------------- | ---------------------------- |
| Geração de testes (unit., integração, aceitação) | Sim                   | Criação de testes unitários  |
| Execução de testes automatizados                 | Parcial               | Integração com pipelines AWS |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações                  |
| --------------------------------- | --------------------- | ----------------------------------------- |
| CI/CD                             | Sim                   | Diagnóstico de falhas em pipelines        |
| Automação                         | Sim                   | Correções sugeridas automaticamente       |
| Monitoramento                     | Sim                   | Integração com console AWS                |
| Documentação técnica automatizada | Sim                   | Logs e relatórios gerados automaticamente |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações              |
| ----------------------- | --------------------- | ------------------------------------- |
| Correções automatizadas | Sim                   | Agentes de transformação de código    |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | Parcial               | Sugestão de tarefas      |
| Execução                            | Parcial               | Assistência contínua     |
| Controle                            | Parcial               | Monitoramento indireto   |
| Encerramento                        | N/A                   |                          |
| Gestão de riscos                    | Parcial               | Alertas de arquitetura   |
| Estimativas (tempo, custo, esforço) | Parcial               | Baseadas em histórico    |
| Medição                             | Parcial               | Métricas via AWS         |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação               | Observações |
| ----------------------------------- | ----------------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐⭐            |             |
| Profundidade técnica                | ⭐⭐⭐⭐⭐            |Forte em AWS |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            |Alta integração |
| Clareza                             | ⭐⭐⭐⭐              |             |
| Aderência às melhores práticas      | ⭐⭐⭐⭐⭐            |AWS Well-Architected|
| Consistência entre respostas        | ⭐⭐⭐⭐⭐            |             |
| Ocorrência de alucinações           | Baixa                   |RAG reduz erros  |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

* Geração de funções
* Refatoração
* Criação de testes

### ● Resultados quantitativos

* Redução significativa de tempo
* Baixa taxa de erros
* Código alinhado às práticas AWS

### ● Exemplos (copie trechos de código, respostas etc.)

* Problema: A build não cria uma aplicação de página única nem exporta para a pasta de saída.

* Solução: Olhe o conteúdo do arquivo.next.config.mjs

Se o código tiver a seguinte configuração padrão: const nextConfig = {};

Modificá-lo da seguinte forma:  const nextConfig = {
                                output: 'export',
                                distDir: 'out',
                                };

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Integração profunda com AWS

* Suporte completo ao ciclo de vida

### **Limitações**

* Forte dependência do ecossistema AWS

* Alguns serviços da AWS não estão disponíveis em todas as regiões da AWS

* Não roda localmente

* Amazon Q Developer pode realizar apenas uma tarefa de desenvolvimento por vez
---

#  **8. Riscos, Custos e Considerações de Uso**

* Dependência de vendor (AWS)

* Custos recorrentes

* Código processado na nuvem

---

#  **9. Conclusão Geral da Análise**

* Geral: A ferramenta mostrou-se adequada para diverssas atividades de Engenharia de Software, principalmente aquelas que tem relação com o ciclo de vida de deenvolvimento

* Ela é adequada para: 

 Geração e revisão de código — pode escrever trechos e funções completas com base em instruções em linguagem natural e contexto do projeto no IDE. 

 Acelerar tarefas repetitivas — como criação de testes unitários e documentação. 

 Assistência integrada no IDE e CLI — ajudando a navegar em bases de código complexas e sugerindo melhorias. 

 Auxílio em tarefas de integração com AWS — diagnósticos, otimização de recursos e workflows de DevOps. 

 Auxílio em ciência de dados/ML (quando integrado a SageMaker Canvas).

* Contudo, deve ser evitada em alguins cenários porque:

Tem dependência forte do ecossistema AWS: Funcionalidades mais profundas (diagnóstico de recursos, integração com serviços AWS) só fazem sentido se o projeto estiver na AWS. 

É uma ferramenta menos madura versus concorrentes: Relatos internos e de usuários indicam que precisão e UX às vezes ficam atrás de rivais como Copilot ou Cursor. 

Não substitui conhecimento técnico: Há críticas de que respostas podem ser imprecisas, levando desenvolvedores a confiar sem verificação manual. 


Projetos offline ou sem AWS: Não é ideal se o ambiente de desenvolvimento for local ou sem necessidade de integração com AWS. 

Em equipes que prezam por controle total sobre ambiente de IA sem dependência de nuvem, ou que valorizam precisão acima de conveniência, outras opções podem ser melhores.

* Atualemte a ferramenta Q Developer se encontra em maturidade avançada, integra LLMNs por meio do AWS Bedrock, o que pode proporcionar:

Integração com IDEs e CLI com respostas em tempo real. 

Geração de código contextual baseada no workspace real. 

Recursos agênticos capazes de executar ações no projeto.

* Vale a pena para a organização?

Acredito que não valha a pena utilizá-la uma vez que tem grande dependência de AWS e outra ferramentas pode fazer o mesmo trabalho de maneira igual ou melhor sem o comprometimento da ligação com nuvem

---

#  **10. Referências e Links Consultados**

* Documentação oficial

https://aws.amazon.com/pt/q/developer/
https://docs.aws.amazon.com/pt_br/q/latest/developer-guide/what-is-q-developer.html
https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/use-q-developer-as-coding-assistant-to-increase-productivity.html
https://docs.aws.amazon.com/pt_br/q/latest/developer-guide/security-scans.html
https://docs.aws.amazon.com/pt_br/q/latest/developer-guide/code-transformation.html
https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html
https://aws.amazon.com/bedrock/
https://aws.amazon.com/q/pricing/

* Fõruns e Discussões

https://www.reddit.com/r/aws/comments/1nbruui/am_i_the_only_one_that_cant_stand_amazon_q/

* Extensão VS Code

https://marketplace.visualstudio.com/items?itemName=AmazonWebServices.amazon-q-vscode

* Benchmarks independentes

https://www.businessinsider.com/amazon-q-lags-revenue-race-competitors-ai-coding-2025-9

