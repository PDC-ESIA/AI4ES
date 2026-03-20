# 1. Identificação da Ferramenta

| Item                            | Descrição                                                                      |
|---------------------------------|--------------------------------------------------------------------------------|
| *Nome da ferramenta*          |       OutSystems Mentor                                                                         |
| *Fabricante / Comunidade*     |          OutSystems                                                                       |
| *Site oficial / documentação* |      [Platform Overview - Mentor](https://www.outsystems.com/low-code-platform/mentor-ai-app-generation/) / [Documentation - Build apps with AI](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/build_apps_with_ai/)                                                                          |
| *Tipo de ferramenta*          | Recurso de geração/refino de aplicações por IA dentro da plataforma low-code OutSystems Developer Cloud (ODC).  | 
| *Licença / acesso*            | Comercial. Acesso via conta/licença/trial.                                            |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                | Descrição                                                    |
|-------------------------------------|--------------------------------------------------------------|
| *Tipo de IA Generativa*           | LLM (interpretação de linguagem natural) + arquitetura “agentic AI” (orquestração de agentes) aplicada à geração/refino de apps.                         |
| *Nome do Modelo*                  | Não divulgado. |
| *Versão*                          | Não divulgado.                                                            |
| *Tamanho (nº de parâmetros)*      | Não divulgado                                                |
| *Acesso*                          | API Privada/Gerenciada (o usuário não acessa o modelo diretamente, interage via IDE/Portal)                          |
| *Suporte a Fine-tuning*           | Não                     |
| *Suporte a RAG*                   | Não exposto/ não configurável pelo usuário no Mentor (no escopo do teste).                                                      |
| *Métodos de prompting suportados* | Prompting em Linguagem Natural (Chat), Upload de Arquivos de Requisitos (PDF/Docx)                            |
| *Ferramentas adicionais*          | Fora do escopo do teste: AI Agent Builder (para criar seus próprios agentes), AI Mentor Studio (Dashboard de Dívida Técnica).    |

---

# 3. Contexto de Execução

| Item                                  | Descrição                               |
|---------------------------------------|-----------------------------------------|
| *Onde roda?*                        | Cloud (OutSystems Developer Cloud – ODC).                 |
| *Infraestrutura utilizada no teste* | Ambiente SaaS gerenciado pela OutSystems (ODC).    |
| *Custos (quando aplicável)*         | Modelo baseado em subscrição anual, sob cotação. Edição Pessoal é gratuita (limitada a 100 usuários internos). |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              |         N/A              | Exige que o usuário defina o app via prompt ou faça o upload de um arquivo de requisitos já existente.                          |
| Análise                 |         N/A              | Não realiza a análise de engenharia.                         |
| Priorização             |         N/A              |                          |
| Modelagem               |         Sim              | Permite modelar e automatizar processos de negócio visualmente, gerando modelos de dados e lógica.                          |
| Validação / Verificação |         N/A              |                          |
| Documentação            |         N/A              |                          |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais |        N/A               |                          |
| Decisões arquiteturais           |        N/A               |                          |
| Avaliação de trade-offs          |        N/A               |                          |
| Uso de padrões arquiteturais     |        N/A               |                          |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto |          N/A             |                          |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código |         Sim              | Geração full-stack e de agentes autônomos. Gera apps completos (dados, lógica, UI) e permite criar agentes que planejam e chamam ferramentas de forma autônoma.                          |
| Refatoração       |         Sim              | Melhoria contínua de código e lógica. IA sugere melhorias para refatorar e aprimorar o código existente de forma ágil                         |
| Detecção de bugs  |         Sim              | Detecção proativa de falhas e validação.                         |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) |         N/A              |                          |
| Execução de testes automatizados                 |         N/A              |                          |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             |        Sim               | Deploy contínuo integrado à plataforma.                          |
| Automação                         |        Sim               | Orquestra o trabalho entre humanos e IA em workflows automatizados complexos.                          |
| Monitoramento                     |        Sim              | Rastreia o raciocínio dos agentes, a qualidade das respostas e os custos de execução em tempo real.                          |
| Documentação técnica automatizada |        N/A               |                          |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas |        Parcial               | Alguns padrões permitem auto-fix.                          |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        |         N/A               |                          |
| Execução                            |         Sim              | Orquestra times de IA. Gerencia o crescimento da força de trabalho de agentes, mantendo o controle e o alinhamento.                        |
| Controle                            |         N/A               |                          |
| Encerramento                        |         N/A               |                          |
| Gestão de riscos                    |         N/A              |                          |
| Estimativas (tempo, custo, esforço) |         N/A             |                          |
| Medição                             |         N/A              |                           |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐⭐            | Geração altamente aderente à plataforma e ao modelo interno.             |
| Profundidade técnica                | ⭐⭐⭐⭐            | Capaz de gerar lógica full-stack (dados, lógica e UI) e arquiteturas multi-agente complexas. Profunda dentro do ecossistema OutSystems; limitada fora dele.            |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            | Utiliza o contexto de metadados da plataforma (Data Fabric) para garantir que toda ação seja contextual e confiável.             |
| Clareza                             | ⭐⭐⭐⭐            | Ações claras, porém pouco explicadas.             |
| Aderência às melhores práticas      | ⭐⭐⭐⭐⭐            | Aplica revisões assistidas por IA em tempo real para garantir padrões de arquitetura, segurança e performance.             |
| Consistência entre respostas        | ⭐⭐⭐⭐⭐            | Alta consistência por operar sobre estado global do projeto.            |
| Ocorrência de alucinações           | Baixa | A IA opera sobre metamodelos internos, reduzindo invenções.             |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

- Geração de aplicação full-stack a partir de prompt textual e documento de requisitos.
- Análise automática de qualidade e aplicação de correções sugeridas.

### ● Resultados quantitativos

- Tempo com IA: Criação de um sistema web completo e funcional em minutos utilizando a IA.
- Tempo sem IA: Dias/semanas.
- Número de erros: Minimizados por "automated security checks" e revisões automáticas.
- Qualidade do código: Alta aderência a padrões Enterprise; monitoramento de qualidade via dashboard centralizado.

### ● Exemplos (copie trechos de código, respostas etc.)

---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Arquitetura Agêntica: Criação de agentes que raciocinam, planejam e utilizam ferramentas de forma autônoma para resolver objetivos.
* Geração full-stack com consciência sistêmica.
* Redução significativa do tempo de entrega inicial.

### **Limitações**

* Dependência de Ecossistema: Desempenho e "confiança" máximos ocorrem apenas dentro do runtime proprietário da OutSystems.
* Complexidade de Customização: Embora gere o "Full-Stack", desvios manuais profundos da arquitetura sugerida podem exigir alta senioridade na plataforma.
* Baixa explicabilidade das ações da IA.

---

#  **8. Riscos, Custos e Considerações de Uso**

* Dependência de vendor: O software gerado e os agentes criados são indissociáveis da infraestrutura ODC (OutSystems Developer Cloud).
* Custos recorrentes: Baseados em subscrição; requer monitoramento de custos de IA em tempo real para evitar surpresas com consumo de tokens.
* Execução Local: Inexistente; a geração e o monitoramento são estritamente Cloud-Native.

---

#  **9. Conclusão Geral da Análise**

O OutSystems Mentor representa um nível mais avançado de maturidade em AI4SE quando comparado a geradores de UI tradicionais, atuando como um agente de engenharia de software orientado à plataforma. É altamente adequado para aceleração de desenvolvimento corporativo padronizado, mas deve ser evitado em cenários que exigem liberdade arquitetural, portabilidade ou controle fino das decisões técnicas.

---

#  **10. Referências e Links Consultados**

- [Mentor AI App Generation - OutSystems](https://www.outsystems.com/low-code-platform/mentor-ai-app-generation/)
- [Build Apps with AI - Documentation](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/build_apps_with_ai/)
- [Agent AI Workbench - OutSystems](https://www.outsystems.com/low-code-platform/agentic-ai-workbench/)
- [Autonomous AI Guide - OutSystems](https://www.outsystems.com/ai/autonomous-ai/)

# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

- [x] Tipo de interface: Chat, autocomplete, comandos ou agente?
    - Híbrida. Possui Chat/Agente (Mentor) para gerar apps do zero a partir de prompts/arquivos , Comandos Visuais e Dashboards (AI Mentor Studio) para análise de qualidade.
   
- [x] Integração: Funciona dentro do editor/IDE ou é ferramenta separada?
    - Integrado dentro da versãoo web.
    
- [x] Facilidade inicial: Consegui usar nos primeiros 5 minutos sem tutoriais?
    - Sim. Para a função gerar um app do zero com o Mentor AI, a barreira é baixa,  bastanto descrever o app que deseja. Entretanto, não é tão intuitivo quanto às alterações via IA. Para desenvolvimento profundo (lógica complexa), exige aprendizado da plataforma visual.

## 2. Contexto do Projeto

- [x] Lê arquivos automaticamente: Preciso colar código ou ela vê o projeto?
    - O Mentor consegue ler documentos de requisitos (PDF, Word) para gerar a aplicação inicial. O AI Mentor Studio lê automaticamente todos os módulos do ambiente (factory) para análise.
- [x] Entende a stack: Detecta linguagens/frameworks ou preciso explicar tudo?
    -Ele é especializado na stack proprietária da OutSystems. Ele "conhece" todas as tabelas, ações e APIs disponíveis no seu ambiente (Data Fabric) e usa isso para sugerir conexões.
- [ ] Múltiplas linguagens: Funciona bem com mais de uma linguagem?
    - Ele suporta a geração de SQL, mas não é uma ferramenta de propósito geral para escrever Python/Java.

## 3. Modo de Trabalho

- [x] Nível de autonomia: Só sugere ou também modifica arquivos sozinha?
    - **Alta Autonomia**. Ele não apenas sugere alterações, mas cria o banco de dados, as telas, a lógica de segurança e os fluxos de trabalho inteiros e publica a aplicação.
- [ ] Controle do usuário: Posso revisar antes de aceitar mudanças?
    - Não há revisão do usuário. Ao selecionar adicionar alteração, ele já realiza a modificação.
- [x] Escopo das ações: Mexe em 1 arquivo por vez ou vários simultaneamente?
    - **Vários**. Diferente de assistentes de código comuns, o Mentor cria/altera múltiplas camadas ao mesmo tempo, criando tabelas no banco de dados, gerando APIs de back-end e criando telas de front-end em uma única execução.

## 4. Capacidades Observadas

- [x] Completude: Gera blocos inteiros de código ou apenas linhas soltas?
    - Blocos completos/Apps inteiros. Gera aplicações funcionais "Full-Stack" (Interface + Dados + Lógica)
- [ ] Explicação: Possui funcionalidade dedicada para explicar código (botão/comando)?
    - Não possui explicações.
- [x] Correção: Possui comandos explícitos de /fix ou "Debug this"?
    - Sim (Via AI Mentor Studio). Ele identifica padrões de erro (Performance, Segurança, Manutenibilidade) e oferece sugestões de correção. Para alguns padrões simples, existe "Auto-fix". A arquitetura agêntica também se "auto-corrige" durante a geração para garantir que o código compile.
- [ ] Referências: Cita de onde tirou a informação (fontes) ou gera sem referência?
    - Não aplicável.

## 5. Limitações Importantes

- [x] Vinculada a plataforma específica: Força uso de serviços (ex: AWS, Azure)?
    - Sim. O OutSystems Mentor é exclusivo para gerar aplicações na plataforma OutSystems. O código gerado depende do runtime da plataforma.
- [x] Restrições de linguagem/stack: Tem tecnologias que não suporta bem?
    - Focado exclusivamente em desenvolvimento Web/Mobile moderno e Cloud-Native. Não é adequado para scripts de sistema.
- [x] Curva de aprendizado: Precisa de muito treino pra usar direito?
    - Média. Usar o chat para gerar o app é trivial. No entanto, para manter, refatorar e evoluir o que a IA criou, é necessário conhecimento técnico de desenvolvimento OutSystems.
