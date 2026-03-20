# Time 1: Requisitos (Engenharia de Prompt & NLP)

**Coordenação:** Dr. Ernesto
**Líder Operacional:** Karlla

## Diretrizes Gerais
* **Paralelismo:** Atuação em paralelo e simultânea com os demais times desde o dia 1.
* **Norteador (TACO IDE):** O time de requisitos deve pegar o repositório do TACO IDE e conversar com o time do TACO IDE para gerar o input orientador inicial do projeto.
* **MVP:** Entregar um Agente MVP analista de requisitos atuando sob coordenação de um **Agente Supervisor (Orquestrador)**. O Agente de Requisitos receberá o input fatiado do Supervisor (fluxo sequencial) e devolverá as Histórias de Usuário (HU) estruturadas para ele.
* **Tools / Subagents:** Utilizar *Agent Tools* apenas para ações de I/O externas e determinísticas com o framework ADK. Usar *Subagentes* caso o processamento de fatiamento do documento matriz torne-se complexo.
* **Gestão de Branches & Pull Requests:** Cada time terá sua própria branch (ex: `feature/time1-requisitos`). O código principal (`main`) é de responsabilidade estrita do Time 4.
* **Quebra de Subtasks e Prazos:** Todas as subtasks abaixo devem ser quebradas em tarefas menores pelos responsáveis, contendo prazos definidos.
* **Critério de Conclusão (DoD):** Ao finalizar uma subtask menor, o responsável (ou seu Agente) deve realizar o *commit* e abrir um *Pull Request (PR)* para a branch do time, que só será "mergeado" após revisão do TechLead/Líder Operacional (Karlla).
* **Doubt Artifacts (Interação Humana):** Obrigatoriamente, todos os agentes devem gerar arquivos de dúvida (`Doubt_Artifact.md`) caso encontrem inconsistências ou bloqueios, pausando a execução do nó para que um humano (Supervisor Orquestrador ou Líder Operacional) consiga interagir.

## Tasks da Líder Operacional (Karlla)
* [ ] **Interação TACO IDE:** Estabelecer contato com o time do TACO IDE, extrair o conceito inicial e converter os insumos do repositório em um contexto estruturado para o time.
* [ ] **Padronização do Output:** Definir o template Markdown para as User Stories (HU), Casos de Uso (UC) e Requisitos (RF/RNF/RN).
* [ ] **Setup do ADK Local:** Configurar o esqueleto do projeto no Google ADK (Python) para o "Agente Analista".
* [ ] **Gestão do Fluxo de Dúvidas:** Consolidar os arquivos `Doubt_Artifact.md` e agendar revisões frequentes com o coordenador.
* [ ] **Alinhamento do Agente MVP:** Garantir a entrega e integração do Agente MVP de requisitos, certificando que ele consuma e retorne os dados no formato exigido pelo Agente Supervisor.

## Subtasks dos Membros

### Adriam (Desenvolvimento)
* [ ] **Subtask 1.1:** Criar e testar as tools em Python para o Agente Analista (fatiamento de documentos e busca de termos específicos). *(Prazo e quebra a definir pelo responsável)*
* [ ] **Subtask 1.2:** Estruturar a base do ADK para receber as definições de regras do sistema. *(Prazo e quebra a definir pelo responsável)*

### Elisa (Prompt Engineering)
* [ ] **Subtask 2.1:** Desenvolver e refinar o System Prompt do agente analista focando no primeiro MVP extraído. *(Prazo e quebra a definir pela responsável)*
* [ ] **Subtask 2.2:** Aplicar técnicas de Few-Shot Prompting para diferenciar as Regras de Negócio de Requisitos Funcionais. *(Prazo e quebra a definir pela responsável)*

### Natalie (Validação de Domínio)
* [ ] **Subtask 3.1:** Atuar no papel de "Cliente", analisando se a extração gerada condiz com a lógica extraída do TACO IDE. *(Prazo e quebra a definir pela responsável)*
* [ ] **Subtask 3.2:** Enriquecer constantemente o artefato de dúvidas com regras ocultas ao LLM. *(Prazo e quebra a definir pela responsável)*

### Todos os Membros
* [ ] **Subtask 4.1:** Executar individualmente seus agentes propostos, focando em estruturar o primeiro fluxo de comunicação inter-agentes para o Agente MVP. *(Abertura de PR para a branch `feature/time1-requisitos` requerida para conclusão).*
