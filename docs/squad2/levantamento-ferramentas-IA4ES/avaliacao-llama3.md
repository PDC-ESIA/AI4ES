#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          | Llama 3 (família de modelos)                                                                        |
| **Fabricante / Comunidade**     | Meta Platforms, Inc                                                                               |
| **Site oficial / documentação** | [Llama 3](https://www.llama.com/models/llama-3/), [Llama 3.2](https://www.llama.com/docs/model-cards-and-prompt-formats/llama3_2/)                                                                               |
| **Tipo de ferramenta**          | LLM de propósito geral |
| **Licença / acesso**            | Llama 3.2 Community License (uso permitido para pesquisa e aplicações comerciais, sujeito a termos específicos definidos pela Meta, incluindo restrições de redistribuição e requisitos de conformidade)|

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | LLM (Large Language Model)                        |
| **Nome do Modelo**                  | Llama 3.2 |
| **Versão**                          | Llama 3.2 3B |
| **Tamanho (nº de parâmetros)**      | 3B (standard)                                                |
| **Acesso**                          | API comercial / Open-source / Local                          |
| **Suporte a Fine-tuning**           | Sim - Full, LoRA, QLoRA, RLHF, RLVR                    |
| **Suporte a RAG**                   | Sim                                                      |
| **Métodos de prompting suportados** | Linguagem natural, Zero-shot, Few-shot, Chain-of-Thought (limitado), In-Context Learning                            |
| **Ferramentas adicionais**          | LangChain, LangGraph, Ollama, Groq...    |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Local / Cloud                 |
| **Infraestrutura utilizada no teste** | GPU: NVIDIA RTX 3060 12GB / CPU: Intel i7 + 16GB RAM    |
| **Custos (quando aplicável)**         | Local: R$ 0 |

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
| Elicitação              | Sim                   | O que faz: gera questionamentos sobre o domínio, analisa contextos, resume atas e reuniões, analisa pontos, transforma descrições em requisitos estruturados. <br> Evidência: Teste realizado para sistema de biblioteca - gerou perguntas sobre usuários, funcionalidades e restrições. Incluiu considerações e sugestões. <br> Limitação: Perguntas genéricas sem profundidade em segurança/performance quando sem orientação explícita.                         |
| Análise                 | Sim                       | O que faz: Identifica conflitos, ambiguidades e inconsistências em requisitos. <br> Como faz: Analisa o conjunto de requisitos fornecidos e aponta problemas lógicos. Evidência: Teste com requisitos conflitantes ("sistema rápido" + "dados localmente" + "acessível de qualquer lugar") - identificou 2/3 conflitos e propôs sugestões. <br> Limitação: Não priorizou automaticamente quais conflitos são críticos vs secundários.                          |
| Priorização             | Sim                   | O que faz: Aplica métodos de priorização (MoSCoW, Kano, Value vs Effort). <br> Como faz: Classifica requisitos quando método é especificado no prompt. <br> Evidência: Aplicou MoSCoW corretamente para features de sistema, com justificativas básicas. <br> Limitação: Não considera espontaneamente dependências técnicas ou restrições de negócio. Justificativas superficiais sem análise de impacto quantitativo, quando não solicitado.                         |
| Modelagem               | Sim                   | O que faz: Gera diagramas UML (texto) de domínio, classes, modelos de dados, fluxo do sistema. <br> Como faz: Cria representações textuais de modelos de requisitos.|
| Validação / Verificação | Sim                  | O que faz: Sugere estratégias de validação e identifica problemas de viabilidade técnica, alinhamento, inconsistências e ambiguidade. |
| Documentação            | Sim | O que faz: Gera documentos de especificação de requisitos (SRS) a partir de especificações. <br> Como faz: Estrutura documento com seções padrão (Introdução, Requisitos Funcionais/Não-Funcionais, Restrições). <br> Evidência: Gerou SRS para sistema de agendamento de consultas com estrutura completa e organizada. <br> Limitação: Conteúdo superficial e genérico. Adequado como template inicial, não como documento final de produção. Requer detalhamento significativo por analista humano. |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | Sim                   | O que faz: Propõe arquiteturas com componentes e integrações. <br> Como faz: Descreve textualmente a arquitetura ou gera código para ferramentas de diagramação (Mermaid, PlantUML). <br> Evidência: Criou arquitetura de microsserviços para e-commerce com serviços de catálogo, carrinho, pagamento e notificações. Especificou comunicação via REST e listou benefícios (escalabilidade, manutenibilidade). <br> Limitação: Gera código de diagrama, não imagem direta. Arquiteturas tendem a ser padrão/genéricas sem consideração de restrições específicas do projeto (orçamento, equipe, timeline) a menos que explicitadas.                         |
| Decisões arquiteturais           | Sim                       | O que faz: Gera ADRs (Architecture Decision Records) comparando alternativas. <br> Como faz: Lista contexto, alternativas, decisão e justificativa. <br> Evidência: Gerou ADR para escolha SQL vs NoSQL em rede social. Listou trade-offs, escolheu SQL com justificativa adequada.                       |
| Avaliação de trade-offs          | Sim                      | O que faz: Compara alternativas arquiteturais listando prós/contras. <br> Como faz: Analisa múltiplas dimensões (performance, custo, complexidade, manutenibilidade).                          |
| Uso de padrões arquiteturais     | Sim                      | O que faz: Explica e exemplifica padrões (MVC, Layered, Event-Driven, CQRS). <b> Como faz: Fornece definição, diagrama conceitual e exemplo de implementação. <br> Evidência: Explicou MVC corretamente com exemplo de aplicação web demonstrando separação de responsabilidades. <br> Limitação: Pode fornecer resposta simplificada/didática, dependendo da qualidade do prompt e do que foi solicitado. |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Sim                   | O que faz: Identifica oportunidades para padrões GoF (Singleton, Factory, Strategy, Observer, etc.) e sugere implementação. <br> Como faz: Gera código com padrão aplicado e explica contexto de uso. <br> Evidência: Implementou Singleton com thread-safety corretamente, explicou quando usar. Criou Strategy Pattern para sistema de pagamento (Pix, boleto, cartão) com estrutura extensível.                         |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Sim | O que faz: Gera funções, classes e módulos a partir de descrições em linguagem natural. <br> Como faz: Traduz requisitos textuais em código executável, conforme linguagem solicitada.                          |
| Refatoração       | Sim                       | O que faz: Identifica code smells e aplica refatorações (extração de métodos, refatoração de condicional, correção de bugs...). <br> Como faz: Analisa código fornecido e propõe versão melhorada. <br> Evidência: Refatorou função com magic numbers e condicionais complexas - extraiu constantes, simplificou lógica, melhorou legibilidade.                          |
| Detecção de bugs  | Sim                       | O que faz: Analisa código e identifica erros de lógica, sintaxe. <br> Como faz: Analisa e traz o código corrigido e/ou aponta linhas problemáticas com explicação.                          |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | Sim                       | O que faz: Cria casos de teste unitários (pytest, unittest) e esboços de testes de integração. <br> Como faz: Analisa função/módulo e gera testes cobrindo casos normais e edge cases. <br> Limitação: Testes gerados precisam de validação (podem não cobrir todos os edge cases reais). Não executa os testes para validar se estão corretos.                         |
| Execução de testes automatizados                 | N/A                      | Atua como gerador de artefatos de teste, não como executor.. Gera scripts de teste mas não os executa. Não valida se os testes passam ou falham. Não integra com frameworks de CI/CD para execução automatizada.                         |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Parcial                   | O que faz: Gera workflows de CI/CD (GitHub Actions, GitLab CI, Jenkins pipelines). <br> Como faz: Cria arquivos YAML/Groovy com stages de build, test, deploy. <br> Evidência: Não testado diretamente, mas baseado em capacidade de gerar código estruturado, espera-se suporte adequado. <br> Limitação: Configurações de produção (secrets, ambientes, rollback) requerem customização por DevOps.                         |
| Automação                         | Parcial                   | O que faz: Escreve scripts Bash/Python para tarefas de automação (backup, deploy, limpeza).                         |
| Monitoramento                     | Parcial                   | O que faz: Sugere ferramentas (Prometheus, Grafana) e escreve queries básicas. <br> Limitação: Não configura infraestrutura de monitoramento. Não analisa métricas em tempo real. Papel é consultivo/assistente de escrita de configuração.                         |
| Documentação técnica automatizada | Parcial                      | O que faz: Gera README, docstrings, comentários inline, documentação de API. <br> Como faz: Analisa código e gera documentação descritiva.                         |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | Parcial | O que faz: Analisa descrição do bug + código e sugere correção. <br> Limitação: Não valida se correção funciona (não executa testes). Correções para bugs complexos/sistêmicos podem ser inadequadas.                         |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | Sim                      | O que faz: Gera esboços de cronogramas, WBS (Work Breakdown Structure), roadmaps. <br> Como faz: Estrutura atividades com estimativas genéricas e dependências.                         |
| Execução                            | Sim                      | O que faz: Auxilia na comunicação (redigir status reports, atas de reunião). <br> Limitação: Não gerencia projeto ativamente. Não rastreia progresso real vs planejado. Papel é assistente de comunicação, não PM autônomo.                         |
| Controle                            | Sim                      | O que faz: Analisa desvios quando fornecidos dados de progresso. <br> Limitação: Não coleta dados de progresso. Não acessa ferramentas de gestão (Jira, Asana). Análise depende de humano fornecer informações.                         |
| Encerramento                        | Sim                      | Capacidade para gerar relatórios e documentação final. Limitação: Necessita de especificações.                         |
| Gestão de riscos                    | Sim                      | O que faz: Lista riscos comuns para tipo de projeto e sugere mitigações. <br> Limitação: Não identifica riscos específicos do projeto sem contexto detalhado.                        |
| Estimativas (tempo, custo, esforço) | Sim                      | O que faz: Estima story points, sugere analogias com projetos similares.Como faz: Análise de complexidade baseada em critérios de aceitação. <br> Limitação: Sem dados históricos (via RAG), estimativas são especulativas. Não considera velocidade real da equipe ou capacidade de recursos.                         |
| Medição                             | Sim                      | O que faz: Sugere KPIs relevantes e interpreta métricas fornecidas.Limitação: Não calcula métricas automaticamente. Não acessa dados de ferramentas de gestão. Papel é consultivo.                         |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐            | Gera código funcional, arquiteturas coerentes e documentação estruturada. Alta precisão em tarefas de complexidade baixa-média (CRUD, requisitos, refatoração). Para bibliotecas populares e padrões estabelecidos, os resultados são consistentemente corretos.            |
| Profundidade técnica                | ⭐⭐⭐⭐⭐            | Fornece explicações claras e contextualizadas. Consegue justificar escolhas arquiteturais, explicar trade-offs e detalhar conceitos de ES.            |
| Contextualização no código/problema | ⭐⭐⭐⭐            | Mantém contexto adequadamente em conversas típicas de desenvolvimento. Compreende requisitos fornecidos, adapta soluções ao contexto descrito e mantém consistência em múltiplas interações sobre o mesmo problema.            |
| Clareza                             | ⭐⭐⭐⭐⭐            | Respostas fáceis de entender e bem organizadas. Explica conceitos de forma didática, sem jargões desnecessários. Estrutura respostas logicamente (contexto → solução → explicação). Código é legível com nomes descritivos. Formatação em Markdown facilita leitura (títulos, listas, blocos de código). Adequado tanto para iniciantes quanto desenvolvedores experientes.             |
| Aderência às melhores práticas      | ⭐⭐⭐⭐            | Segue padrões de qualidade automaticamente. Código limpo, estruturado e funcional. Aplica princípios de engenharia de software quando orientado (SOLID, padrões GoF, convenções de estilo). Raramente sugere práticas inseguras. Para adicionar elementos avançados (type hints completos, docstrings detalhadas), basta solicitar explicitamente.             |
| Consistência entre respostas        | ⭐⭐⭐            | Variação moderada com configurações padrão. Mesmo prompt pode gerar respostas com abordagens ligeiramente diferentes (ex: traz métodos de ordenação diferentes ao solicitar algoritmo sem especificar). Pequena variação na implementação de funções com mesmo prompt. Estrutura geral se mantém, mas detalhes variam.            |
| Ocorrência de alucinações           | Baixa | Rara em bibliotecas populares e conceitos estabelecidos.             |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

- Experimento 1: User Stories (Requisitos - Modelagem)
  - Tarefa: Gerar User Stories para sistema de biblioteca universitária
 
- Experimento 2: Gerar diagramas
  - Tarefa: Gerar diagrama uml para sistema de gerenciamento de consultas médicas

- Experimento 3: ADR (Arquitetura - Decisões)
  - Tarefa: Escolher SQL vs NoSQL para rede social usando Architecture Decision Record

- Experimento 4: Debugging (Construção - Detecção de bugs)
  - Tarefa: Identificar e corrigir bug em função Python

- Experimento 5: CRUD (Construção - Geração de código)
  - Tarefa: Criar classe Java para sistema de gerenciamento de consultas médicas

- Experimento 6: Testes Unitários (Testes - Geração)
  - Tarefa: Gerar suite de testes pytest para função de divisão com edge cases
 
- Experimento 7: Testes Unitários (Testes - Geração)

### ● Resultados quantitativos

* Tempo com IA x sem IA
  * Com IA: 30s - 2 min (geração + validação)
  * Sem IA: 15-45 min (escrita + debug + consulta docs)
* Número de erros: Nenhum erro de execução identificado nos experimentos.
* Qualidade do código: alta com uso da IA. Código gerado segue PEP 8, estrutura clara, variáveis descritivas.
* Cobertura de testes: Alta, com geração consistente de cenários positivos e negativos.
* Comentários qualitativos: A IA acelerou significativamente o desenvolvimento inicial, reduzindo esforço operacional sem comprometer a clareza ou a correção das soluções produzidas.

### ● Exemplos (copie trechos de código, respostas etc.)

---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* O Llama possui licença aberta, permitindo uso comercial, adaptação do modelo, fine-tuning e implantação em ambientes locais, sem cobrança de licenças proprietárias.
* As versões mais recentes da família Llama apresentam resultados próximos aos de modelos proprietários.
* Eficiência operacional, podendo ser executado em infraestruturas mais modestas.,
* Privacidade dos dados, permitindo que organizações mantenham dados sensíveis sob seu próprio domínio, evitando o envio de informações para serviços externos ou nuvens de terceiros.

### **Limitações**

* Embora competitivo, o Llama ainda tende a ficar abaixo de modelos como GPT-5 ou Claude 3 em tarefas que exigem raciocínio profundo, diálogos longos ou alta robustez cognitiva.
* Execução local pode exigir conhecimento técnico.
* Custo e complexidade do fine-tuning: rocessos de adaptação do modelo demandam hardware especializado, datasets bem preparados e conhecimento técnico avançado, o que pode elevar tempo e custo do projeto.

---

#  **8. Riscos, Custos e Considerações de Uso**

*Respostas incorretas ou imprecisas: exigindo validações adicionais em contextos críticos.
* Custos recorrentes:
  * Execução em nuvem: consumo de GPU por tempo de uso
  * Execução local: investimento inicial em hardware e custos contínuos de manutenção
  * Fine-tuning: uso intensivo de GPU e preparação de dados
* Limitações em privacidade ou compliance: dependendo do domínio de aplicação, pode ser necessário garantir aderência a normas como LGPD, GDPR ou outras regulações setoriais.
* Dificuldades de execução local: pode exigir capacidade técnica da equipe responsável por sua operação e manutenção.

---

#  **9. Conclusão Geral da Análise**

* A ferramenta é adequada para quais atividades de ES?

  O Meta Llama (3.2) mostra-se adequado para diversas atividades de Engenharia de Software, especialmente aquelas que exigem flexibilidade, customização e controle sobre o ambiente de execução. O modelo pode apoiar tarefas como geração e revisão de código, criação de testes, análise de logs, apoio à documentação técnica, definição arquitetural e moelagem, além de integração em pipelines internos via RAG ou fine-tuning com dados próprios.
  
* Em quais casos deve ser evitada?

  Seu uso deve ser evitado em cenários que demandam mais alto nível de desempenho imediato, raciocínio extremamente complexo ou forte garantia de estabilidade sem esforço operacional. Em projetos que não dispõem de equipe técnica qualificada para operar infraestrutura de IA, gerenciar modelos e mitigar riscos como alucinações e falhas de segurança, soluções proprietárias via API tendem a ser mais adequadas. 
  
* Em qual maturidade técnica ela se encontra?

  O Llama encontra-se em um estágio avançado, com modelos estáveis, documentação consolidada e amplo ecossistema de ferramentas. Apesar de não alcançar consistentemente o topo absoluto em benchmarks frente a modelos fechados de última geração, sua evolução recente demonstra solidez suficiente para uso em produção, especialmente em ambientes controlados.
  
* Vale a pena para a organização?

  Sim, vale a pena para empresas e instituições que priorizam controle de dados, redução de dependência de fornecedores, possibilidade de customização e custos previsíveis. Para organizações que aceitam maior complexidade técnica em troca de autonomia e flexibilidade, o Llama representa uma boa alternativa e estrategicamente relevante no cenário atual de IA generativa.
---

#  **10. Referências e Links Consultados**

* [Llama 3](https://www.llama.com/models/llama-3/)
* [Llama downloads](https://www.llama.com/llama-downloads/)
* [Llama 3.2](https://www.llama.com/docs/model-cards-and-prompt-formats/llama3_2/)
