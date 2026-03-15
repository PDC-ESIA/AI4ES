# Time 4: Codificação & DevOps/LLMOps (Infra Local & ADK)

**Coordenação:** Dra. Mariana
**Líder Operacional:** Danillo

## Diretrizes Gerais
* **Paralelismo:** Atuação em paralelo e simultânea com os demais times desde o dia 1.
* **Norteador (TACO IDE):** O time de codificação deve **obrigatoriamente** usar o repositório, códigos-fonte e regras de negócio/requisitos do TACO IDE como guia. Além disso, deverá gerar os próprios códigos referenciando esses requisitos integrados.
* **MVP:** Garantir a entrega de um Agente MVP Coder subordinado ao **Agente Supervisor**. Este agente atua no esquema *Paralelo com Feedback Loop* junto ao Time de Testes, implementando as bases dos diagramas e Requisitos encaminhados pelo orquestrador.
* **Tools / Subagents:** Considerar fortemente a criação de um **Subagente Refatorador** acoplado ao Coder principal caso a complexidade ciclomática do projeto saia de controle. *Agent Tools* focadas em commit, I/O e branch managament.
* **Manutenção da Branch Main:** O fluxo de Git da branch `main` é de responsabilidade estrita deste time. O Time 4 atua como centralizador dos merges de todas as branches de feature locais dos outros times (`feature/time1`, `feature/time2`, etc). O Time 4 também trabalha em sua própria `feature/time4-codificacao`.
* **Quebra de Subtasks e Prazos:** É mandatório desmembrar as subtasks abaixo em pacotes menores com prazos fixados.
* **Critério de Conclusão (DoD):** Para cada entrega atômica completada (seja do humano ou do Agente Coder), gerar o *commit* e um *Pull Request (PR)* à respectiva branch, a ser inspecionado pelo Líder Operacional (Danillo) antes de aceitar e empurrar para a `main`.
* **Doubt Artifacts (Interação Humana):** Obrigatoriamente, todos os agentes devem gerar arquivos de dúvida (`Doubt_Artifact.md`) caso encontrem inconsistências, pausando a execução do nó aguardando intervenção.

## Tasks do Líder Operacional (Danillo)
* [ ] **Referencial de Código:** Sincronizar o contexto para utilizar o projeto matriz (TACO IDE) como principal referencial para a base de código do Agente Coder.
* [ ] **Git Flow & Configuração Local:** Desenhar o Git Flow focado na forte paralelização (para evitar bloqueios dos outros times). Servidor ou branch management limpo.
* [ ] **Integração de APIs LLM:** Gerenciar as chaves e rate limits das APIs de LLMs (como OpenRouter, Groq, etc) para suportar a carga múltipla dos testes de comunicação do Agente MVP.
* [ ] **SCM/LLMOps:** Integração do fluxo de versionamento comum com scripts de Git/DVC nos ciclos de entrega dos agentes.

## Subtasks dos Membros

### Ana Karolina (Otimização de PRD & Eficiência)
* [ ] **Subtask 1.1:** Fracionamento de Requisitos: Quebrar PRDs fornecidos (Time 1 a partir do TACO) em painéis lógicos de menor contexto. *(Prazo e quebra a definir pela responsável)*
* [ ] **Subtask 1.2:** Construir "Context Windows" claras aos Agentes baseados nesse fracionamento, contendo metadados JSON/Markdown otimizados. *(Prazo a definir pela responsável)*

### Walisson (DevOps & Versioning)
* [ ] **Subtask 2.1:** Configurar script ou pipeline CI/CD que valide o sucesso de commits executados pelos Agentes. *(Prazo e quebra a definir pelo responsável)*

### Gabriel Brandão (Agente Revisor de PR)
* [ ] **Subtask 2.2:** Desenvolver e integrar um Agente especializado em revisar Pull Requests (PRs), validando padrões de código, testes e requisitos do TACO IDE antes de autorizar o merge para a branch `main`. *(Prazo a definir pelo responsável)*

### Danilo Galvão (Prompt Engineering do Agente Coder)
* [ ] **Subtask 3.1:** Afiar as instruções sistêmicas do LLM para processar requerimentos modulares em base das antigas e novas bibliotecas orientadas do TACO. *(Prazo e quebra a definir pelo responsável)*
* [ ] **Subtask 3.2:** Promover revisões contínuas nos prompts limitando arquiteturas indesejadas frente ao alinhamento do Time 2. *(Prazo a definir pelo responsável)*

### Heitor (ADK Tooling & Repositório)
* [ ] **Subtask 4.1:** Escrever tools em Python que integrem operações Git (Add, Commit, branch checkout) com dependência de verificação humana pré-commit. *(Prazo e quebra a definir pelo responsável)*

### Todos os Membros
* [ ] **Subtask 5.1:** Liderar os testes de comunicação do Agente MVP Coder com o **Agente Supervisor**, assegurando o fluxo paralelo com a área de QA e promovendo a entrega do evento de integração. *(Aprovação final do PR na branch `feature/time4-codificacao` e posterior merge para a `main`)*.
