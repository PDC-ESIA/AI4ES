#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          |                        Open Code Interpreter                                                         |
| **Fabricante / Comunidade**     |              Pesquisadores da Multimodal Art Projection Research Communit, University of Waterloo, Allen Institute for Artificial Intelligence, HKUST e IN.AI Research                                                                  |
| **Site oficial / documentação** |                [Site Oficial](https://opencodeinterpreter.github.io/)                                                                |
| **Tipo de ferramenta**          | Assistente de código open-source com execução e refinamento iterativo |
| **Licença / acesso**            | Open-source (código, modelos e datasets abertos)                                              |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | LLM especializado em código                         |
| **Nome do Modelo**                  | ex.: CodeLlama e DeepSeekCoder |
| **Versão**                          |   Variantes baseadas em CodeLlama-Python e DeepSeekCoder-Base/Instruct                                                           |
| **Tamanho (nº de parâmetros)**      | 6.7B, 7B, 13B, 15B, 33B, 34B, 70B                                                |
| **Acesso**                          | Open-source / Local (Checkpoints disponíveis)                          |
| **Suporte a Fine-tuning**           | Sim (Modelos foram fine-tuned por 3 épocas com learning rate de 2e-5)                     |
| **Suporte a RAG**                   | Não mencionado no artigo                                                      |
| **Métodos de prompting suportados** | Self-Refine e Self-Correction                            |
| **Ferramentas adicionais**          | Não mencionado no artigo   |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Local (Modelos open-source projetados para serem baixados e executados)                 |
| **Infraestrutura utilizada no teste** | Modelos de grande escala (ex: 33B, 70B) sugerem necessidade de GPUs robustas, embora o hardware específico de inferência do usuário não seja detalhado, o treinamento usou GPUs de alta capacidade implícitas pelo tamanho.    |
| **Custos (quando aplicável)**         | Gratuito (software). Custos associados apenas ao hardware de execução local ou nuvem privada. |

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
| Elicitação              |           N/A            |          O foco é a implementação técnica de instruções já dadas.                |
| Análise                 |           N/A            |          Não mencionado.                |
| Priorização             |           N/A            |          Não mencionado.                |
| Modelagem               |           N/A            |          Não mencionado.                |
| Validação / Verificação |           N/A            |          Foco em validação de código, não de requisitos.                |
| Documentação            |           N/A            |          Foco em documentação de código (comentários), não de requisitos.                |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais |         N/A              |        Foco em geração de código, não em design de sistemas complexos.                  |
| Decisões arquiteturais           |         N/A              |        Não mencionado.mencionado.                  |
| Avaliação de trade-offs          |         N/A              |        Não mencionado.mencionado.                  |
| Uso de padrões arquiteturais     |         N/A              |        Não mencionado.mencionado.                  |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto |        Sim               |      O treinamento em Melhores Práticas e Escalabilidade  capacita o assistente a sugerir e implementar padrões de projeto adequados durante o refinamento do código.                   |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código |        Sim               |    Função primária da ferramenta, treinada em 68K interações.                      |
| Refatoração       |        Sim               |    O modelo realiza refinamento iterativo baseado em feedback sobre eficiência, clareza e recursos.                      |
| Detecção de bugs  |        Sim               |    Aponta possíveis bugs ou erros lógicos no código e sugere maneiras de corrigi-los.                      |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) |      Sim                 |      O assistente é capaz de gerar scripts de teste (ex: unittest, pytest).                    |
| Execução de testes automatizados                 |       Sim                |      O modelo gera scripts de teste como parte da sua capacidade de codificação.                    |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             |      N/A                 |     Não mencionado.                     |
| Automação                         |      N/A                 |     Não mencionado.                     |
| Monitoramento                     |      N/A                 |     Não mencionado.                     |
| Documentação técnica automatizada |      N/A                 |     Não mencionado.                     |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas |     Sim                  |    O modelo possui um fluxo específico de correção de código onde tenta corrigir erros de execução ou lógica iterativamente.                      |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        |       N/A                |   Não mencionado.                       |
| Execução                            |       N/A                |   Não mencionado.                       |
| Controle                            |       N/A                |   Não mencionado.                       |
| Encerramento                        |       N/A                |   Não mencionado.                       |
| Gestão de riscos                    |       N/A                |   Não mencionado.                       |
| Estimativas (tempo, custo, esforço) |       N/A                |   Não mencionado.                       |
| Medição                             |       N/A                |   Não mencionado.                       |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            |             | Não foi possível acessar o Open Code Interpreter para realizar a avaliação.            |
| Profundidade técnica                |             | Não foi possível acessar o Open Code Interpreter para realizar a avaliação.            |
| Contextualização no código/problema |             | Não foi possível acessar o Open Code Interpreter para realizar a avaliação.           |
| Clareza                             |             | Não foi possível acessar o Open Code Interpreter para realizar a avaliação.            |
| Aderência às melhores práticas      |             | Não foi possível acessar o Open Code Interpreter para realizar a avaliação.            |
| Consistência entre respostas        |             | Não foi possível acessar o Open Code Interpreter para realizar a avaliação.            |
| Ocorrência de alucinações           |             | Não foi possível acessar o Open Code Interpreter para realizar a avaliação.            |

---

#  **6. Experimentos Realizados**

Não foi possível acessar o OpenCodeInterpreter para realizar experimentos.

---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Integração de Execução: Capacidade de rodar o código, ler o erro do compilador e se auto-corrigir.
* Desempenho Open-Source: O modelo 33B compete diretamente com o GPT-4 proprietário.
* Refinamento Iterativo: Não gera apenas uma resposta, mas melhora a solução através de múltiplos turnos de diálogo.

### **Limitações**

* Dificuldade em corrigir múltiplos erros simultâneos ou complexos em poucas tentativas (limite de iterações).
* A performance máxima (91.6) depende de feedback humano sintetizado do GPT-4.
* Pode enfrentar dificuldades com intenções de usuário extremamente complexas ou ambíguas.

---

#  **8. Riscos, Custos e Considerações de Uso**

* Como o modelo gera e executa código, há riscos de segurança. O artigo menciona a necessidade de verificar vulnerabilidades e não expor informações sensíveis, sugerindo que a execução deve ser isolada.
* Rodar modelos de 33B ou 70B parâmetros localmente exige hardware de ponta (GPUs com alta VRAM), o que pode ser um custo de infraestrutura.
* Risco de propagação de vieses presentes nos datasets de treino open-source.

---

#  **9. Conclusão Geral da Análise**

* Altamente adequada para codificação e correção de bugs
* Alta maturidade técnica para um modelo de pesquisa/open-source, estabelecendo um novo estado da arte (SOTA) para modelos abertos.
* Vale a pena para organizações que buscam uma alternativa self-hosted (local) ao GitHub Copilot ou GPT-4, com capacidade de auto-correção, desde que possuam infraestrutura para rodar os modelos.

---

#  **10. Referências e Links Consultados**

* [Site oficial](https://opencodeinterpreter.github.io/)
* [Artigo](https://arxiv.org/pdf/2402.14658)
---
* OBS: Todas as informações foram obtidas com base no site oficial e no artigo. Algumas questões não foram respondidas, visto que não foi possível acessar o Open Code Interpreter para a realização de testes.
