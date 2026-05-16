# Time 2: Design & Prototipagem (Arquitetura de Agentes)

**Coordenação:** Dra. Mariana
**Líder Operacional:** Jeniffer

## Diretrizes Gerais
* **Paralelismo:** Atuação em paralelo e simultânea com os demais times desde o dia 1.
* **Norteador (TACO IDE):** Utilizar o Gemini para gerar UC/HU e RF/RNF/RN com base no repositório do TACO IDE.
* **MVP:** Entregar um Agente MVP arquiteto/designer subordinado ao **Agente Supervisor**. Ele receberá as Histórias de Usuário (HU) já validadas do Supervisor após a fase do Time 1, processando-as e devolvendo os diagramas de volta para a orquestração.
* **Tools / Subagents:** Utilizar *Agent Tools* para parser e save de diagramas (`.puml` / `.md`). Subagentes arquitetos específicos podem atuar sobre trade-offs muito vastos.
* **Gestão de Branches & Pull Requests:** Cada time terá sua própria branch (ex: `feature/time2-design`). A branch `main` só recebe merges aprovados e operados pelo Time 4.
* **Quebra de Subtasks e Prazos:** As subtasks elencadas devem ser destrinchadas em tarefas atômicas com prazos estipulados pelos membros.
* **Critério de Conclusão (DoD):** A finalização de cada tarefa menor culmina obrigatoriamente num *commit* e na abertura de um *Pull Request (PR)* para a branch do time, a ser verificado pela Líder Operacional (Jeniffer).
* **Doubt Artifacts (Interação Humana):** Obrigatoriamente, todos os agentes devem gerar arquivos de dúvida (`Doubt_Artifact.md`) caso encontrem inconsistências ou bloqueios, pausando a execução do nó para intervenção humana.

## Tasks da Líder Operacional (Jeniffer)
* [ ] **Organização do Agente MVP:** Estruturar o fluxo de comunicação do Agente MVP de design, garantindo que ele consuma automaticamente as diretrizes enviadas pelo **Agente Supervisor**.
* [ ] **Padronização de Diagramas:** Definir diretrizes para agentes usarem Mermaid ou PlantUML como padrão em Markdown, possibilitando versionamento Git via texto.
* [ ] **Definição da Arquitetura do Agente:** Estruturar "Agente Arquiteto" para justificar os trade-offs técnicos.
* [ ] **Orquestração do Protótipo Mockado:** Definir estrutura de página estática (HTML/CSS básico) que servirá de tela inicial na jornada.
* [ ] **Consolidação das Justificativas:** Reunir saídas de justificativas técnicas dos agentes para validação de manutenibilidade com a coordenadora.

## Subtasks dos Membros

### Leonardo Cortes (Prompt Engineering)
* [ ] **Subtask 1.1:** Desenvolver prompts de "Chain-of-Thought" para que o agente gere diagramas de arquitetura, justificando suas escolhas. *(Prazo e quebra a definir pelo responsável)*

### Matheus Augusto (ADK Tooling)
* [ ] **Subtask 2.1:** Desenvolver tools no ADK (Python) que permitam o salvamento autônomo de diagramas gerados nos formatos adequados (`.md` ou `.puml`) na pasta do repositório. *(Prazo a definir pelo responsável)*
* [ ] **Subtask 2.2:** Integrar e monitorar processo de escrita local dos agentes. *(Prazo a definir pelo responsável)*

### Libna (Prototipagem de Interface)
* [ ] **Subtask 3.1:** Auxiliar no desenvolvimento da comunicação do Agente MVP, garantindo que a interface gerada reflita o processo do TACO baseado nos insumos da IA. *(Prazo a definir pela responsável)*
* [ ] **Subtask 3.2:** Reservar/Desenhar o fluxo de interação voltado ao "tutor socrático". *(Prazo a definir pela responsável)*

### Todos os Membros
* [ ] **Subtask 4.1:** Auxiliar na execução em laboratório e revisão local do fluxo de comunicação, garantindo que o Agente MVP esteja integrado a tempo. *(PR para `feature/time2-design`)*.
