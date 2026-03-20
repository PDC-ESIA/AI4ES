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
| **Suporte a Fine-tuning** | Sim (via BYOM). Embora a plataforma foque em RAG, a arquitetura aberta permite que as equipes tragam os seus próprios modelos que podem ter sido fine-tuned externamente para frameworks internos.  |
| **Suporte a RAG** | Sim (Nativo). Usa RAG para indexar semanticamente todo o código, documentação e logs de erros, garantindo contexto real sem re-treinar o modelo.  |
| **Métodos de prompting suportados** | Chain Prompts , Iterative Prompting, e Context-Aware Prompts.  |
| **Ferramentas adicionais** | Extensões para VS Code e JetBrains; Integração com Git (PRs automáticos), Jira e CLI.  |

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

    NOTA: TODAS AS INFORMAÇÕES ABAIXO SERÃO BASEADAS APENAS EM DOCUMENTAÇÃO E EXPERIENCIAS DE TERCEIROS. TESTES NÃO FORAM REALIZADOS POR IMPEDIMENTO DA PRÓPRIA EMPRESA (LICENSA, PROBLEMAS PARA ACESSAR A CLOUD, IMPEDIMENTO DO USO DO CODEASSISTENT, INEXISTÊNCIA DE UM CHAT, ENTERPRISE).
---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              | Baixo / N/A           | A ferramenta não possui funcionalidades de entrevista ou "chatbot de elicitação" para stakeholders de negócio. O foco é na etapa posterior (Engenharia). |
| Análise                 | Médio     | O módulo Software Engineering Insights (SEI) analisa o fluxo de tickets (Jira) para identificar gargalos e clareza, mas não analisa semanticamente o texto dos requisitos para consistência lógica. |
| Priorização             | Médio   | Utiliza métricas DORA e o framework Trellis para ajudar gestores a priorizar tarefas baseadas em impacto e esforço histórico, mas não prioriza por "valor de negócio" automaticamente. |
| Modelagem               | N/A                   | Não há evidências na documentação oficial de que a ferramenta gere diagramas UML ou modelos de domínio a partir de texto de requisitos. |
| Validação / Verificação | Alto (Verificação)    | Através do "Intent-based testing", a IA valida se o código atende à "intenção" descrita, funcionando como uma verificação automatizada do requisito técnico. |
| Documentação            | Médio                 | Gera documentação técnica (ex: descrições de Pull Requests) que servem como rastro do requisito implementado, mas não gera o Documento de Requisitos (SRS) inicial. |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | Alto (Foco em Infra/DevOps) | A funcionalidade "Architect Mode" atua como um arquiteto virtual, desenhando workflows e pipelines de entrega complexos através de conversa. Nota: O foco é na arquitetura de implantação e infraestrutura, não na geração de diagramas de classes/UML da aplicação em si. |
| Decisões arquiteturais           | Médio | A IA auxilia na escolha de estratégias de rollout e define políticas de governança que restringem ou guiam a arquitetura de nuvem permitida. |
| Avaliação de trade-offs          | Médio | O módulo Cloud Cost Management (CCM) utiliza IA para analisar o trade-off entre custo e performance da infraestrutura, sugerindo mudanças arquiteturais para otimização. |
| Uso de padrões arquiteturais     | Alto | Facilita a adoção de padrões modernos como Microservices e Serverless através de templates de Golden Pipelines. A ferramenta impõe padrões de "GitOps" nativamente na sua operação. |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Médio / Alto  | A ferramenta não possui um menu "Inserir Design Pattern", mas o Code Agent utiliza Busca Semântica para identificar e sugerir a reutilização de padrões já existentes no seu repositório. Além disso, as funcionalidades de Refatoração Automatizada podem sugerir a aplicação de padrões para limpar "code smells", dependendo do LLM utilizado (GPT-4/Claude). |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Alto (De acordo com a documentação) / N/A (Não pôde ser testado) | O Code Agent gera código completo, scripts e arquivos de configuração (YAML/Terraform) a partir de linguagem natural. Diferencia-se por usar RAG (Retrieval Augmented Generation) para entender o contexto do repositório inteiro, gerando código que respeita as convenções e variáveis existentes no projeto, ao invés de snippets genéricos. |
| Refatoração       | Alto (Foco em Segurança/Qualidade) / N/A (Não Testado) | Através do Automated Code Review, a IA sugere refatorações específicas durante o Pull Request. O recurso de Auto-Remediation vai além, permitindo que a IA aplique a refatoração automaticamente no código para corrigir vulnerabilidades de segurança detectadas (ex: atualizar uma lib depreciada). |
| Detecção de bugs  | Alto/Medio  | Utiliza o Pipeline Error Analyzer e TI (Test Intelligence) para detectar bugs. A ferramenta analisa logs de builds falhos anteriores para prever se uma mudança de código tem alta probabilidade de quebrar o build , alertando o desenvolvedor antes mesmo da execução completa. Na prática, não me retornou uma análise sobre o erro da pipeline em questão (provavelmente por ser FreeTrial). |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | Alto / N/A (Não pode ser testado) | A funcionalidade "Intent-based testing" permite gerar scripts de teste (incluindo End-to-End e Unitários) apenas descrevendo o cenário em linguagem natural (ex: "Verifique se o login falha sem senha"). O Code Agent também gera testes unitários dentro da IDE usando o contexto do arquivo aberto (segundo a documentação, portanto não testado). |
| Execução de testes automatizados                 | Muito Alto / N/A (Não pôde ser testado) | O recurso "Smart Test Selection" utiliza ML para analisar o grafo de chamadas do código e executar apenas os testes afetados pela mudança (reduzindo o tempo de ciclo em até 80%). Além disso, possui Self-Healing: se um seletor de UI muda (ex: botão muda de ID), a IA ajusta o teste automaticamente para não quebrar a execução. |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Muito Alto (Nativo) | A ferramenta utiliza IA generativa (AIDA) para criar e corrigir pipelines de CI/CD automaticamente. O recurso "Pipeline Error Analysis" diagnostica falhas de build instantaneamente, explicando a causa raiz e sugerindo a correção (ex: "Versão do Java incompatível"). OBS: Nos testes, essa feature não pôde ser observada (plano FreeTrial). |
| Automação                         | Alto | Possui recursos avançados de GitOps e Chaos Engineering (Chaos Guard) orquestrados por IA. A IA também gera políticas de conformidade (OPA - Open Policy Agent) a partir de texto, automatizando a governança da operação. |
| Monitoramento                     | Alto (Verificação Contínua) | Embora não substitua ferramentas como o Datadog, ela integra-se a elas através do módulo Continuous Verification (CV). Utiliza ML não-supervisionado para analisar logs e métricas em tempo real após um deploy, detectando anomalias sutis que humanos ou alertas estáticos perderiam. |
| Documentação técnica automatizada | Alto | Gera automaticamente Release Notes detalhados, descrições de Pull Requests e relatórios de incidentes. A IA resume o "o que mudou" em linguagem natural para stakeholders não-técnicos. |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | Alto | A ferramenta possui capacidades robustas de Auto-Remediation. No nível de código, ο módulo STO (Security Testing Orchestration) com IA pode gerar Pull Requests automáticos para corrigir vulnerabilidades (ex: atualizar bibliotecas depreciadas). No nível de infraestrutura, a IA aciona rollbacks automáticos ou executa scripts de correção se a verificação pós-deploy falhar. |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | Médio (Baseado em Dados) | A ferramenta não substitui o Jira/Project para criar o cronograma. No entanto, o módulo SEI correlaciona dados de capacidade da equipe e histórico de entrega para auxiliar no planejamento de sprints, identificando gargalos antes que eles atrasem o plano. |
| Execução                            | Alto | Fornece visibilidade em tempo real do fluxo de valor. A integração com tickets permite rastrear o progresso de cada feature desde o commit até a produção, orquestrando a execução do trabalho técnico. |
| Controle                            | Alto (Governança) | Implementa "Governance as Code" via OPA (Open Policy Agent). A IA pode bloquear pipelines automaticamente se desvios forem detectados (ex: custo excessivo, falta de aprovação), exercendo controle rígido sobre o projeto sem intervenção manual. |
| Encerramento                        | N/A | Por focar em Entrega Contínua (fluxo infinito), a ferramenta não possui funcionalidades específicas para "encerramento formal de projeto" (Termo de Aceite, Lições Aprendidas estáticas), pois a aprendizagem é contínua via dashboards. |
| Gestão de riscos                    | Alto | O recurso de Change Impact Analysis utiliza IA para pontuar o risco de cada alteração de código. O Security Testing Orchestration (STO) insere a gestão de risco de vulnerabilidades diretamente no pipeline de entrega. |
| Estimativas (tempo, custo, esforço) | Médio (Foco em Custo/Lead Time) | O módulo Cloud Cost Management (CCM) é excelente para estimar e prever custos financeiros do projeto. Para estimativa de tempo/esforço (horas-homem), utiliza métricas de Lead Time histórico. |
| Medição                             | Muito Alto | Automatiza a coleta e análise das Métricas DORA (Deployment Frequency, Lead Time for Changes, MTTR, Change Failure Rate) e métricas de satisfação do desenvolvedor, eliminando planilhas manuais de medição de projeto. |

---

# 5. Critérios de Qualidade da Resposta da IA

| Critério | Avaliação  | Justificativa / Observação |
| :--- | :---: | :--- |
| **Precisão** | N/A | Não foi possível avaliar o conteúdo da resposta, pois a ferramenta não retornou output nos testes realizados (timeout/vazio), embora a interface da IA estivesse presente. |
| **Relevância** | ⭐⭐⭐⭐⭐ | (Baseado na interface): A IA é altamente contextual. O botão de ajuda ("Ask AIDA") aparece especificamente no ponto de falha do pipeline ou na linha de código do PR, demonstrando alta relevância contextual, sem necessidade de copiar e colar logs externos. |
| **Clareza** | N/A | Não avaliado (sem retorno de texto). |
| **Completude** | N/A | Não avaliado. |
| **Consistência** | ⭐ | A disponibilidade do serviço mostrou-se inconsistente. Em múltiplos testes (Chat, PR, Pipeline), a IA ora estava inacessível, ora não retornava dados, indicando instabilidade na camada de serviço Free/Trial. |

---

# 6. Experimentos Realizados

### 6.1. Escopo dos Testes
O objetivo foi validar as capacidades de **Geração de Código**, **Refatoração** e **Operações (Diagnóstico de Erros)** utilizando a versão SaaS (Harness Cloud) com uma conta de avaliação (Free Tier).

Os testes foram gerados de acordo com as limitações que foram encontradas ao longo do estudo da IA. Haviam mais testes (que estão formulados e documentados, inclusive) que não chegaram a ser feitos devido às barreiras que surgiram.
### 6.2. Testes Executados
1.  **Automação de Code Review:** Criação de Pull Request contendo erro lógico (`for loop` com índice inválido) para verificar detecção automática.
2.  **Pipeline Error Analysis:** Execução de pipeline CI/CD com erro de script (`ech` vs `echo`) para testar o diagnóstico de causa raiz pela IA.

### 6.3. Resultados Observados
* **Barreira de Acesso:** A funcionalidade de IA não é "plug-and-play". Foi necessário configurar infraestrutura de nuvem (Harness Cloud) e inserir dados de cartão de crédito para habilitar a execução básica.
* **Falha de Resposta:** No teste de Pipeline, o botão de assistência da IA ("Analyze Error") foi exibido corretamente na interface de logs, comprovando a existência da feature. Contudo, ao ser acionado, o serviço não retornou nenhuma explicação (retorno vazio/nulo), impossibilitando a validação da qualidade da resposta.
* **Conclusão do Experimento:** A ferramenta demonstrou alta complexidade de configuração e baixa disponibilidade do serviço de IA generativa na camada de teste.


    
---

# 7. Pontos Fortes e Fracos

| Pontos Fortes (Vantagens) | Pontos Fracos (Desvantagens) |
| :--- | :--- |
| **Integração Profunda:** A IA atua majoritariamente de forma passiva por detrás do repositório e gerenciando pipelines. Ela tem acesso ao contexto completo da aplicação sem alucinar sobre dados externos. | **Barreira de Entrada Elevada:** Exige configuração complexa de infraestrutura (Delegates, Connectors, Kubernetes) apenas para testar algo simples como um "Hello World". Não é amigável para desenvolvedores individuais. |
| **Foco em Operações:** Diferente de ferramentas focadas apenas em gerar código, a Harness brilha na gestão do ciclo de vida: deploy, rollback automático e governança. | **Dependência de Licenciamento:** As funcionalidades de IA parecem estar restritas ou instáveis em planos gratuitos, dificultando a validação de valor antes da compra. |
| **Governança e Segurança:** Recursos como "Policy as Code" e "Chaos Guard" orquestrados por IA oferecem um nível de controle empresarial que assistentes de código comuns não possuem. | **UX Fragmentada:** A interface mistura conceitos clássicos de DevOps com IA de forma densa. Opções vitais (como ativar a IA no repo) são difíceis de encontrar. |

---

# 8. Riscos, Custos e Considerações de Uso

* **Riscos de Adoção:**
    * **Complexidade Técnica:** A curva de aprendizado é alta. Equipes sem maturidade em DevOps (Docker/K8s) terão dificuldade em fazer a IA funcionar.
    * **Instabilidade do Serviço:** Nos testes, a IA falhou em retornar respostas simples (no caso, sequer chegou a retornar algo), o que representa um risco para operações críticas que dependam dela para diagnósticos rápidos.

* **Custos Ocultos:**
    * Além do custo de licença (por usuário/serviço), há o custo de infraestrutura (Harness Cloud ou máquinas próprias para rodar os Delegates) e o custo cognitivo de configuração.

* **Privacidade e Dados:**
    * A ferramenta utiliza modelos híbridos (OpenAI/Google). É necessário revisar os termos de "Zero Retention" para garantir que códigos proprietários não sejam usados para treinar modelos públicos, embora a Harness prometa privacidade robusta (RBA).

---

# 9. Conclusão Geral da Análise

A Harness IA se posiciona como uma plataforma completa de engenharia de software. Sua proposta de valor teórica é imensa, cobrindo desde a geração de código até o monitoramento pós-deploy com correções automáticas.

No entanto, a experiência prática de avaliação revelou uma ferramenta com alta dificuldade para o início do seu uso. Diferente de soluções que entregam valor imediato (como GitHub Copilot ou ChatGPT), a Harness exige uma fundação de infraestrutura robusta para operar. Os testes mostraram que, embora as funcionalidades existam na interface, sua disponibilidade e facilidade de uso na versão de avaliação são limitadas. No próprio site oficial, o uso da IA está desabilitado por padrão em uma configuração consideravelmente escondida e, mesmo após a sua ativação, não foi possível utilizar a IA nos chamados "Code Repositorys" de outra forma sem ser com a configuração de um pipeline. Para isso (pipelines), diria que a IA opera muito bem, embora algumas features (como o "Analyze Error" descrito no tópico 6) da IA não funcionem de forma alguma.

Além disso, a Harness lançou uma extensão CodeAssistant (chamarei de CA a partir de agora) para as IDEs (no meu caso, VSCode), para entrar no mercado competitivo contra o Copilot. Mas, por algum motivo que foge da minha compreensão, não fui capaz de utilizar essa CA, o que me impossibilitou de realizar a maioria dos testes, já que não tive acesso à um chat, CA, e algumas features da criação de CD/CI e pipelines automatizadas que não funcionavam como deveriam e/ou eram extremamente pouco intuitivas. Confesso que se eu tivesse mais tempo, poderia explorar mais sobre algumas capacidades da IA que atestei ser verdadeira (review automático de Pull Requests, por exemplo).

No geral, destaco que a Harness AI é excelentíssima para diversas áreas do desenvolvimento pela sua capacidade nativa de automatizar diversos processos de forma relativamente simples, entretando, nada disso estava acessível para mim no plano "Free/Trial". Minha má experiência não invalida as grandes capacidades que a Harness possui.

**Veredito:** É uma ferramenta recomendada exclusivamente para **Grandes Empresas (Enterprise)** com equipes de Plataforma/DevOps maduras, que buscam governança e automação de ponta a ponta. Para desenvolvedores individuais, startups ou times ágeis que buscam apenas produtividade em codificação, soluções mais leves e diretas são mais indicadas.

---

#  **10. Referências e Links Consultados**

1.  HARNESS INC. **Harness Platform Documentation**. Disponível em: <https://developer.harness.io/>. Acesso durante a realização dos testes.
2.  HARNESS INC. **Harness AI Development Assistant (AIDA)**. Disponível em: <https://www.harness.io/products/platform>.
3.  HARNESS INC. **Pricing & Plans**. Disponível em: <https://www.harness.io/pricing>.
4.  Resultados dos experimentos práticos realizados na plataforma Harness Cloud (Versão Free Tier/Trial) conforme descrito na Seção 6 deste documento.