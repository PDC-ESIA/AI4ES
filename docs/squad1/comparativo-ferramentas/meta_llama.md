#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          |           Meta Llama                                                                     |
| **Fabricante / Comunidade**     |                Meta Platforms, Inc                                                                |
| **Site oficial / documentação** |                  [Docuemntação Meta Llama](https://llama.developer.meta.com/docs/overview/)                                                              |
| **Tipo de ferramenta**          | LLM de Propósito Geral e Modelo de Fundação (Foundation Model). |
| **Licença / acesso**            |  Modelo de pesos abertos (OpenSource sob uma licença comunitária permissiva para uso comercial e pesquisa)                                              |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | LLM / multimodal / híbrido (arquitetura)                         |
| **Nome do Modelo**                  | ex.:  Llama 2, Llama 3, Llama 4 e variantes especializadas como CodeLlama.|
| **Versão**                          | série Llama 4 (multimodais) e Llama 3.1                                                              |
| **Tamanho (nº de parâmetros)**      | Edge: 1B e 3B (Llama 3.2). Standard: 8B e 70B (Llama 3.1). Massive: 405B (Llama 3.1) para tarefas de alta complexidade.                                                |
| **Acesso**                          | API comercial / Open-source (Pesos Abertos) / Local                          |
| **Suporte a Fine-tuning**           | Sim. É o modelo "padrão" para Fine-tuning e LoRA (Low-Rank Adaptation) na comunidade                     |
| **Suporte a RAG**                   | Sim                                                      |
| **Métodos de prompting suportados** | CoT e In-Context Learning Nativos. ReAct, PoT, Self-Refine via Prompt Engineering                           |
| **Ferramentas adicionais**          | LangChain, LangGraph, Ollama, Groq, extensões VSCode etc.    |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Local / Cloud                 |
| **Infraestrutura utilizada no teste** | (GPU (Modelos Grandes), CPU)    |
| **Custos (quando aplicável)**         | Custo por token varia dependendo do provedor de nuvem ou plataforma de hospedagem |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**


---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              |         Sim              | O modelo é frequentemente utilizado para transcrever e resumir reuniões com stakeholders, transformando linguagem natural em requisitos técnicos preliminares. |
| Análise                 |         Sim              |                entende a lógica de sistemas e gera código para renderizadores de diagramas.          |
| Priorização             |         Sim              |                 assistente para processar grandes volumes de dados e aplicar critérios objetivos, como Classificação, Análise de Dependência e Estimativa de Esforço Relativo.          |
| Modelagem               |         Sim              |                modelagem textual que pode ser renderizada visualmente, como gerar diagramas como código, modelagem de dados e modelagem de domínio.          |
| Validação / Verificação |                     Sim  | revisor crítico (QA de requisitos) para garantir que o que foi especificado está correto e alinhado com as necessidades antes de qualquer código ser escrito.|
| Documentação            |         Sim              |                Gera especificações de requisitos e User Stories a partir de rascunhos ou transcrições.          |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | Sim                      |        O Llama não gera o arquivo de imagem .png ou .jpg diretamente. Ele gera o código-fonte que ferramentas de renderização transformam em diagramas.                  |
| Decisões arquiteturais           |       Sim                |            Atua como um "assistente de raciocínio", ajudando arquitetos a ponderar prós e contras (ex: Monolito vs. Microserviços) com base em cenários descritos.              |
| Avaliação de trade-offs          |           Sim            |                O modelo não apenas "lista prós e contras", mas consegue ponderar variáveis conflitantes (como Latência vs. Consistência ou Custo de Desenvolvimento vs. Escalabilidade).          |
| Uso de padrões arquiteturais     |             Sim          |                  O Llama não desenha "caixas e setas" diretamente, mas gera a especificação técnica detalhada da arquitetura.        |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Sim                      |      O Llama (especialmente versões focadas em código) consegue sugerir e implementar padrões (como Singleton, Factory, Strategy) em classes existentes.                    |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Sim                      |      É o principal caso de uso do CodeLlama e Llama 3.1, com alta proficiência em Python, JavaScript, C++, etc.                    |
| Refatoração       |             Sim          |                  Utilizado para limpar código, melhorar legibilidade e modernizar sintaxe.        |
| Detecção de bugs  | Sim                      |       Analisa trechos de código para encontrar erros lógicos ou de sintaxe antes da compilação.                    |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) |Sim                       |     Cria casos de teste unitários e de integração automaticamente baseados na lógica da função fornecida.                     |
| Execução de testes automatizados                 |Sim                       |     Auxilia na escrita de scripts para frameworks como Selenium ou Cypress.                     |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             |Sim                       |     Escreve scripts de shell e pipelines de CI/CD (ex: GitHub Actions).                     |
| Automação                         |Sim                       |     O Llama não substitui o Jenkins ou o Kubernetes, mas ele escreve os scripts e configurações que essas ferramentas usam.                     |
| Monitoramento                     | Sim                      |      transforma o monitoramento de uma atividade passiva de visualização de dashboards em uma atividade ativa de inteligência operacional. Atuando principalmente em Detecção, Análise e Remediação.                    |
| Documentação técnica automatizada |                   Sim    |                        Gera docstrings e arquivos README automaticamente analisando o repositório.  |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas |                  Sim     |                        Propõe patches para erros reportados em logs.  |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | Sim                      |      reduz a "síndrome da página em branco", gerando esboços robustos de documentos essenciais.                    |
| Execução                            | Sim                      |      o foco do Llama é a comunicação e a remoção de impedimentos através da clareza da informação.                    |
| Controle                            | Sim                      |       o Llama atua na análise de desvios entre o planejado e o realizado.                    |
| Encerramento                        |     Sim                  |              o modelo é excelente para sintetizar conhecimento acumulado, Lições Aprendidas, Relatório final e Arquivamento.|
| Gestão de riscos                    |     Sim                  |          o Llama utiliza seu vasto conhecimento de treinamento para prever problemas que a equipe pode não ter considerado.                |
| Estimativas (tempo, custo, esforço) | Sim                      |      o Llama auxilia na lógica do cronograma no sequenciamento de atividades e detecção de gargalos. Ajuda a realizar análise de custos e justificativa de orçamento.  Pode ler a descrição de uma User Story e sugerir uma pontuação de complexidade (Fibonacci), justificando sua escolha com base nos critérios de aceitação (atuando como um "dev virtual" na votação). Além disso, se alimentado com dados históricos de projetos anteriores (via RAG), pode comparar o projeto atual com os passados para sugerir estimativas de esforço mais precisas.                    |
| Medição                             | Sim                      |      o Llama pode sugerir quais indicadores (KPIs) são mais relevantes para o tipo de projeto atual e ler os números brutos de desempenho gerando uma análise textual explicativa, diagnosticando se a tendência é positiva ou negativa.                    |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐            |extremamente preciso em lógica, matemática e sintaxe de linguagens populares (Python, JS, Java). Em bibliotecas muito específicas ou recentes (pós-corte de conhecimento), ele pode errar parâmetros de funções.             |
| Profundidade técnica                | ⭐⭐⭐⭐⭐            | Llama tende a ser mais explicativo e didático. Ele não apenas dá o código, mas frequentemente explica o porquê daquela escolha arquitetural, descendo ao nível de gestão de memória ou complexidade algorítmica se instigado.            |
| Contextualização no código/problema | ⭐⭐⭐⭐            | Com a janela de 128k tokens, ele mantém o contexto muito bem. A nota não é 5 porque, em prompts massivos com muitas restrições negativas ("não use X"), ele ocasionalmente ignora uma restrição periférica (fenômeno de Lost in the Middle).            |
| Clareza                             | ⭐⭐⭐⭐⭐            | A formatação do Llama é excelente. Ele estrutura respostas com Markdown, negrito e listas de forma muito legível. Separa claramente o que é explicação, o que é código e o que é nota de rodapé.            |
| Aderência às melhores práticas      | ⭐⭐⭐⭐            | Tende a gerar código "Limpo" (Clean Code) e seguro por padrão. Raramente sugere práticas inseguras (como eval()) sem avisos. Às vezes sugere bibliotecas ligeiramente datadas se não for forçado a usar as mais novas.             |
| Consistência entre respostas        | ⭐⭐⭐⭐            | Tende a gerar código "Limpo" (Clean Code) e seguro por padrão. Raramente sugere práticas inseguras (como eval()) sem avisos. Às vezes sugere bibliotecas ligeiramente datadas se não for forçado a usar as mais novas.            |
| Ocorrência de alucinações           | Baixa | Ele agora admite mais frequentemente que "não sabe" ou que não pode acessar URLs externas. Ainda alucina métodos em bibliotecas de nicho ou referências bibliográficas acadêmicas.            |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

Criar uma classe em Python para gerenciar um banco de dados de "Clientes" (CRUD completo)

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
