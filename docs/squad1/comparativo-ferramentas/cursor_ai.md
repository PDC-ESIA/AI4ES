#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          |                                                                                |
| **Fabricante / Comunidade**     |                                                                                |
| **Site oficial / documentação** |                                                                                |
| **Tipo de ferramenta**          | (ex.: assistente de código, LLM geral, plataforma multimodal, plugin IDE etc.) |
| **Licença / acesso**            | (Comercial, open-source, híbrido)                                              |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | LLM / multimodal / difusão / híbrido                         |
| **Nome do Modelo**                  | ex.: GPT-4.1, Claude 3.5, DeepSeek-Coder, CodeLlama-34B etc. |
| **Versão**                          |                                                              |
| **Tamanho (nº de parâmetros)**      | Se disponível                                                |
| **Acesso**                          | API comercial / Open-source / Local                          |
| **Suporte a Fine-tuning**           | Sim/Não + tipo (LoRA, Full FT, Adapters)                     |
| **Suporte a RAG**                   | Sim/Não                                                      |
| **Métodos de prompting suportados** | CoT, ReAct, PoT, Self-Refine etc.                            |
| **Ferramentas adicionais**          | LangChain, LangGraph, Ollama, Groq, extensões VSCode etc.    |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Local / Cloud / Híbrido                 |
| **Infraestrutura utilizada no teste** | (GPU, CPU, RAM ou serviço utilizado)    |
| **Custos (quando aplicável)**         | Preço por token, por licença ou por uso |

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
