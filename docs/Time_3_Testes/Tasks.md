# Time 3: Testes (Geração e Validação)

**Coordenação:** Dr. Ernesto
**Líder Operacional:** Victor Rangel

## Diretrizes Gerais
* **Paralelismo:** Atuação em paralelo e simultânea com os demais times desde o dia 1.
* **Norteador (TACO IDE):** Utilizar o Gemini para gerar UC/HU e RF/RNF/RN alem de testes unitários e de integração com base no repositório do TACO IDE.
* **MVP:** Entregar um Agente MVP de testes (QA) subordinado ao **Agente Supervisor**. Este agente atua no esquema *Paralelo com Feedback Loop*, recebendo os requisitos finalizados do Supervisor e gerando os testes via *Test-Driven Development (TDD)* simultaneamente à codificação do Time 4.
* **Tools / Subagents:** Ferramentas (*Agent Tools*) estritas para run e parsing de logs de teste (pytest).
* **Gestão de Branches & Pull Requests:** Cada time terá sua própria branch (ex: `feature/time3-testes`). A consolidação na `main` fica sob tutela do Time 4.
* **Quebra de Subtasks e Prazos:** Os encarregados das subtasks têm o dever de quebrar o trabalho em itens menores e colocar prazos para sua conclusão.
* **Critério de Conclusão (DoD):** Com o fim da subtask, cria-se o *commit* e sobe-se um *Pull Request (PR)* contra a branch local do time. A aprovação é dada pelo Líder Operacional (Victor Rangel).
* **Doubt Artifacts (Interação Humana):** Obrigatoriamente, todos os agentes devem gerar arquivos de dúvida (`Doubt_Artifact.md`) caso encontrem inconsistências ou bloqueios, pausando a execução do nó para intervenção humana.

## Tasks do Líder Operacional (Victor Rangel)
* [ ] **Setup do Agente MVP:** Definir e implementar a integração do Agente MVP de QA, garantindo que ele consiga se comunicar e atuar em paralelo recebendo comandos do Supervisor.
* [ ] **Padronização do Framework:** Definir Pytest e as bibliotecas de coverage baseadas na premissa como execução interna dos agentes.
* [ ] **Definição do Fluxo TDD:** Estabelecer como o Agente QA se comunicará com o código gerado em andamento por requisitos e design.
* [ ] **Gestão de Falsos Positivos:** Protocolizar artefato de dúvida `Doubt_Artifact.md` para revisão humana das inconsistências trazidas pela IA.
* [ ] **Infraestrutura Test-Ready:** Garantir o workspace local com dependências testáveis limpas.

## Subtasks dos Membros

### Leonardo Lima (ADK Tooling)
* [ ] **Subtask 1.1:** Estruturar as automações/tools para comando integrado (ex: pytest executado pela IA). *(Prazo e quebra a definir pelo responsável)*

### Filipe (ADK Tooling)
* [ ] **Subtask 1.2:** Estruturar a leitura de log de erro de retorno e lógica para instruir os agentes em tentativas de autocorreção em falhas iniciais. *(Prazo a definir pelo responsável)*

### Vinicius Espindola (Prompt Engineering)
* [ ] **Subtask 2.1:** Configurar prompts de teste para ir além do caminho feliz, cobrindo vulnerabilidades, classes de equivalência e valores-limite do ecossistema estudado. *(Prazo a definir pelo responsável)*

### Brenno (Execução e Verificação)
* [ ] **Subtask 3.1:** Monitorar a geração contínua nos diretórios e relatar as experimentações. *(Prazo a definir pelo responsável)*

### Henrique (Execução e Verificação)
* [ ] **Subtask 3.2:** Avaliar e repassar inconformidades graves ou "alucinações" nos testes unitários para intervenção humana pela Coordenação. *(Prazo a definir pelo responsável)*

### Todos os Membros
* [ ] **Subtask 4.1:** Testar e consolidar o modelo do Agente MVP de testes para rodar os fluxos de validação no primeiro teste prático de comunicação inter-agentes. *(Subir PR para `feature/time3-testes`)*
