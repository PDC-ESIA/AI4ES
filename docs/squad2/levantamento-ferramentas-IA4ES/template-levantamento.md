#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta** | Harness AI (ou Harness AIDA - AI Development Assistant)              |
| **Fabricante / Comunidade** | Harness Inc.            |
| **Site oficial / documentação** | harness.io / developer.harness.io                                    |
| **Tipo de ferramenta** | Plataforma de Entrega de Software (SDLC) AI-Native; inclui Agentes de IA para Codificação (Code Agent), DevOps, QA e Segurança.  |
| **Licença / acesso** | Comercial (SaaS/Enterprise). Possui camadas "Free" para módulos específicos e componentes Open Source (como o Gitness/Drone), mas a IA em si é parte da oferta comercial da plataforma.  |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa** | LLM (Large Language Model) / Híbrido. A plataforma utiliza uma arquitetura de "Agente" que orquestra múltiplos modelos conforme a tarefa (ex: geração de código vs. análise de logs).  |
| **Nome do Modelo** | Multi-modelo: Suporta nativamente OpenAI GPT-4o, Google Gemini Flash e Claude 3.7 Sonnet (num contexto de *Bring Your Own Model* ou integração nativa).  |
| **Versão** | Variável consoante o fornecedor escolhido (ex: GPT-4o, Gemini 1.5 Flash, Claude 3.7 Sonnet).  |
| **Tamanho (nº de parâmetros)** | Não divulgado / Proprietário (depende dos modelos da OpenAI/Google/Anthropic conectados).  |
| **Acesso** | Híbrido. Acesso via API comercial (SaaS) na plataforma Harness, mas com suporte a "Bring Your Own Model" (BYOM) para integrar modelos locais ou privados.  |
| **Suporte a Fine-tuning** | Sim (via BYOM). Embora a plataforma foque em RAG, a arquitetura aberta permite que as equipas tragam os seus próprios modelos que podem ter sido fine-tuned externamente para frameworks internos.  |
| **Suporte a RAG** | Sim (Nativo). Utiliza Retrieval Augmented Generation (RAG) para indexar semanticamente todo o código, documentação e logs de erros, garantindo contexto real sem re-treinar o modelo.  |
| **Métodos de prompting suportados** | Chain Prompts (Cadeia de comandos), Iterative Prompting (Refinamento iterativo), e Context-Aware Prompts (Injeção automática de contexto do repositório/erros).  |
| **Ferramentas adicionais** | Extensões para VS Code e JetBrains; Integração com Git (PRs automáticos), Jira e CLI (Harness AI x Gemini CLI Extension).  |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?** | Modelo Híbrido (SaaS + Local Delegate). A inteligência (AIDA) e o painel de controle rodam na nuvem da Harness (SaaS). A execução das tarefas no seu código roda na sua infraestrutura através de um agente chamado "Harness Delegate".  |
| **Infraestrutura utilizada no teste** | (Requisitos Mínimos Recomendados): Para conectar a sua infraestrutura ao SaaS, é necessário rodar o Harness Delegate (via Docker ou Kubernetes), que exige no mínimo 2 vCPUs e 8GB de RAM por réplica.  |
| **Custos (quando aplicável)** | Modelo "Developer 360" (Por Desenvolvedor). Para módulos de CI e Código, a cobrança é por usuário ativo. Existe um plano Free (Gratuito) que inclui o uso da IA (AIDA) para times pequenos. Para módulos de CD (Deployment), a cobrança pode ser por "Instância de Serviço".  |

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

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              |                       |                          |
| Análise                 |                       |                          |
| Priorização             |                       |                          |
| Modelagem               |                       |                          |
| Validação / Verificação |                       |                          |
| Documentação            |                       |                          |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais |                       |                          |
| Decisões arquiteturais           |                       |                          |
| Avaliação de trade-offs          |                       |                          |
| Uso de padrões arquiteturais     |                       |                          |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto |                       |                          |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código |                       |                          |
| Refatoração       |                       |                          |
| Detecção de bugs  |                       |                          |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) |                       |                          |
| Execução de testes automatizados                 |                       |                          |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             |                       |                          |
| Automação                         |                       |                          |
| Monitoramento                     |                       |                          |
| Documentação técnica automatizada |                       |                          |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas |                       |                          |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        |                       |                          |
| Execução                            |                       |                          |
| Controle                            |                       |                          |
| Encerramento                        |                       |                          |
| Gestão de riscos                    |                       |                          |
| Estimativas (tempo, custo, esforço) |                       |                          |
| Medição                             |                       |                          |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐⭐            |             |
| Profundidade técnica                | ⭐⭐⭐⭐⭐            |             |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            |             |
| Clareza                             | ⭐⭐⭐⭐⭐            |             |
| Aderência às melhores práticas      | ⭐⭐⭐⭐⭐            |             |
| Consistência entre respostas        | ⭐⭐⭐⭐⭐            |             |
| Ocorrência de alucinações           | Baixa/Média/Alta |             |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

(Ex.: gerar CRUD, revisar código Python, criar testes para módulo X etc.)

### ● Resultados quantitativos

* Tempo com IA x sem IA
* Número de erros
* Qualidade do código
* Cobertura de testes
* Comentários qualitativos

### ● Exemplos (copie trechos de código, respostas etc.)

---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* …

### **Limitações**

* …

---

#  **8. Riscos, Custos e Considerações de Uso**

* Dependência de vendor
* Custos recorrentes
* Limitações em privacidade ou compliance
* Barreiras técnicas de adoção
* Dificuldades de execução local
* Restrições para fine-tuning ou RAG

---

#  **9. Conclusão Geral da Análise**

* A ferramenta é adequada para quais atividades de ES?
* Em quais casos deve ser evitada?
* Em qual maturidade técnica ela se encontra?
* Vale a pena para a organização?

---

#  **10. Referências e Links Consultados**

* Documentação oficial
* Artigos
* Tutoriais
* Benchmarks independentes
