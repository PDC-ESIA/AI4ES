# 1. Identificação da Ferramenta
| Item                            | Descrição                                                                      |
|---------------------------------|--------------------------------------------------------------------------------|
| **Nome da ferramenta**          | Cursor AI                                                                      |
| **Fabricante / Comunidade**     | Anysphere Inc. (Fundada em 2022 por Michael Truell, Sualeh Asif, Arvid Lunnemark e Aman Sanger - ex-alunos do MIT) |
| **Site oficial / documentação** | [Site oficial](https://cursor.com) e [Documentação](https://docs.cursor.com)             |
| **Tipo de ferramenta**          | Assistente de código / IDE baseado em IA (fork do Visual Studio Code)         |
| **Licença / acesso**            | Comercial com plano gratuito (Freemium)<br>Planos: Free, Pro ($20/mês), Pro Plus ($60/mês), Ultra ($200/mês), Business (customizado) |

---

# 2. Informações do Modelo de IA Utilizado

## Sistema Multi-Modelo com Modelos Proprietários e de Terceiros

| Item                                | Descrição                                                    |
|-------------------------------------|--------------------------------------------------------------|
| **Tipo de IA Generativa**           | LLM / Multimodal (suporte a texto, código e imagens)         |
| **Nome do Modelo**                  | **Modelos Proprietários do Cursor:**<br>• Cursor Tab (modelo Fusion): Autocomplete personalizado<br>• cursor-small: Predições inline<br>**Modelos de Terceiros:**<br>• OpenAI: GPT-5, GPT-5-Codex, GPT-4.1, GPT-4o, GPT-3.5 Turbo<br>• Anthropic: Claude Opus 4.1, Claude Opus 4, Claude Sonnet 4.5, Claude Sonnet 4, Claude 3.7 Sonnet<br>• Google: Gemini 3 Pro, Gemini 2.5 Pro<br>• xAI: Grok Code |
| **Versão**                          | Cursor IDE: v0.46+ (atualizado continuamente)<br>Modelos: últimas versões dos provedores (dezembro 2025) |
| **Tamanho (nº de parâmetros)**      | Não divulgado para modelos proprietários Cursor.<br>Modelos terceiros: variam (ex: Claude Opus 4 - confidencial, GPT-5 - confidencial) |
| **Acesso**                          | Comercial via API dos provedores + modelos proprietários hospedados pelo Cursor |
| **Suporte a Fine-tuning**           | Não diretamente. Possível usar modelos customizados via API própria (BYOK - Bring Your Own Key) |
| **Suporte a RAG**                   | Sim - através de:<br>• Indexação automática do codebase (embeddings semânticos)<br>• @folders, @files, @docs para contexto específico<br>• Integração com documentação externa |
| **Métodos de prompting suportados** | • Chain-of-Thought (CoT) - via Extended Thinking<br>• ReAct - agentes com ferramentas<br>• Self-Refine - iteração automática<br>• Context injection - @mentions<br>• Instruções customizadas (.cursorrules) |
| **Ferramentas adicionais**          | • Composer/Agent: Edição multi-arquivo<br>• Tab: Autocomplete inteligente<br>• Cmd+K: Edições inline<br>• Chat: Conversação sobre código<br>• Terminal integration: Execução de comandos<br>• GitHub integration: Code review automatizado<br>• Slack/Mobile: Delegação remota de tarefas<br>• MCP (Model Context Protocol): Integração de ferramentas externas<br>• Bugbot: Review automático de PRs |

---

# 3. Contexto de Execução

| Item                                  | Descrição                               |
|---------------------------------------|-----------------------------------------|
| **Onde roda?**                        | **Híbrido:**<br>• IDE: Local (Windows, macOS, Linux)<br>• Modelos: Cloud (infraestrutura US-based)<br>• Agent: Pode rodar remotamente (Background Agent)<br>• Opção de modelos locais via BYOK |
| **Infraestrutura utilizada no teste** | **Cliente Desktop:**<br>• CPU: Qualquer processador moderno<br>• RAM: 4GB+ recomendado<br>• Storage: ~500MB para instalação<br>• Internet: Necessária para modelos cloud<br>**Infraestrutura Cloud (Cursor):**<br>• Servidores US-based<br>• GPUs para inferência (não especificado)<br>• CDN global para baixa latência |
| **Custos (quando aplicável)**         | **Plano FREE ($0/mês):**<br>• Requisições lentas ilimitadas (com fila)<br>• Acesso limitado a modelos premium<br>• Tab autocomplete limitado (2000/mês)<br>**Plano PRO ($20/mês):**<br>• Tab: Ilimitado<br>• Modelo Auto: Ilimitado<br>• $20 em créditos de API (±225 requisições Sonnet 4, ±550 Gemini, ±500 GPT-5)<br>• Uso adicional: $0.04/requisição ou preço API do provedor<br>**Plano PRO PLUS ($60/mês):**<br>• $70 em créditos API (3.5x do Pro)<br>• ±675 Sonnet 4, ±1650 Gemini, ±1500 GPT-5<br>**Plano ULTRA ($200/mês):**<br>• $400 em créditos API (20x do Pro)<br>• ±4500 Sonnet 4, ±11000 Gemini, ±10000 GPT-5<br>• Acesso prioritário a novos recursos<br>• Sem caps de computação<br>**Plano BUSINESS/TEAMS ($40/usuário/mês):**<br>• 500 requisições incluídas/usuário (alguns modelos premium consomem 2+ requisições por chamada)<br>• SSO, Privacy Mode, Admin controls<br>• Analytics e relatórios |

---

# 4. Atividades de Engenharia de Software (SWEBOK)

Para cada item abaixo, descrevemos:
- **O que a ferramenta faz**
- **Como faz**
- **Exemplos / evidências**
- **Limitações observadas**

---

## 4.1. Requisitos de Software

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| **Elicitação**          | **Sim (Parcial)**     | **O que faz:** Utiliza "Chat with Codebase" para extrair requisitos implícitos já existentes no código.<br>**Como faz:** Através de indexação semântica (RAG) do repositório, permite perguntas como "Como o sistema calcula imposto?" ou "Quais são as regras de validação de usuário?"<br>**Exemplo:** Ao perguntar sobre regras de negócio, o Cursor identifica funções relevantes e explica a lógica implementada.<br>**Limitação:** Não captura requisitos de stakeholders externos ou novos requisitos não implementados. |
| **Análise**             | **Sim**               | **O que faz:** Analisa impacto de mudanças em requisitos através de múltiplos arquivos.<br>**Como faz:** O modo "Composer/Agent" permite simular alterações e verificar dependências entre componentes.<br>**Exemplo:** Ao solicitar "adicionar validação de CPF em usuários", analisa quais arquivos (models, schemas, routes, tests) precisam ser modificados.<br>**Limitação:** Análise limitada ao código técnico, não considera impacto em processos de negócio ou conformidade regulatória. |
| **Priorização**         | **Não**               | **Limitação:** Não possui conceito de backlog, user stories ou critérios de priorização (ROI, urgência, valor de negócio). Executa o que é solicitado sem avaliar importância estratégica. |
| **Modelagem**           | **Sim (Parcial)**     | **O que faz:** Interpreta descrições textuais e diagramas simples (Mermaid/PlantUML) para gerar código correspondente.<br>**Como faz:** LLMs processam linguagem natural e convertem em estruturas de código.<br>**Exemplo:** Pode receber um diagrama de classes em Mermaid e gerar as classes Python/TypeScript correspondentes.<br>**Limitação:** Não cria diagramas UML complexos ou modelos visuais abstratos. A modelagem é focada no código em si, não conceitos. |
| **Validação / Verificação** | **Sim**           | **O que faz:** Valida viabilidade técnica de requisitos através do "Shadow Workspace".<br>**Como faz:** Tenta implementar requisitos em background e executa verificações (linting, type checking) antes de sugerir ao usuário.<br>**Exemplo:** Ao pedir "adicionar autenticação JWT", valida se as dependências existem e se a implementação proposta compila sem erros.<br>**Limitação:** Validação puramente técnica. Não valida se o requisito atende necessidades do usuário final ou se está completo. |
| **Documentação**        | **Sim**               | **O que faz:** Gera documentação automática de requisitos implementados.<br>**Como faz:** Analisa código e gera docstrings, READMEs, e explicações em linguagem natural.<br>**Exemplo:** Pode gerar automaticamente um arquivo REQUIREMENTS.md descrevendo funcionalidades implementadas no sistema.<br>**Limitação:** Documentação é reativa (baseada no código existente), não proativa para capturar requisitos ainda não implementados. |

---

## 4.2. Arquitetura de Software

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| **Geração de designs arquiteturais** | **Sim (Parcial)** | **O que faz:** Materializa arquitetura em código e estrutura de pastas.<br>**Como faz:** Baseado em descrições, gera estrutura de projeto seguindo padrões arquiteturais (MVC, Clean Architecture, Hexagonal).<br>**Exemplo:** Pode criar estrutura completa de projeto FastAPI com separação de camadas (models, schemas, routes, services, repositories).<br>**Limitação:** Não cria diagramas arquiteturais visuais (C4, UML) para comunicação com stakeholders não-técnicos. A arquitetura é expressa apenas em código. |
| **Decisões arquiteturais**       | **Sim**               | **O que faz:** Sugere decisões arquiteturais e explica trade-offs.<br>**Como faz:** Através do chat, pode comparar abordagens (REST vs GraphQL, monolito vs microsserviços, SQL vs NoSQL) e justificar escolhas baseadas no contexto do projeto.<br>**Exemplo:** Ao perguntar "devo usar Redis ou Memcached?", fornece análise comparativa considerando o stack existente.<br>**Limitação:** Decisões são baseadas em padrões conhecidos. Pode não considerar restrições específicas de negócio ou regulatórias não explícitas no código. |
| **Avaliação de trade-offs**      | **Sim**               | **O que faz:** Compara diferentes abordagens de implementação.<br>**Como faz:** Via chat interativo, apresenta prós e contras de soluções alternativas.<br>**Exemplo:** "Compare performance entre usar ORM vs SQL raw para este caso específico" - fornece análise contextualizada ao projeto.<br>**Limitação:** Avaliação é qualitativa. Não fornece métricas quantitativas de performance ou benchmarks reais. |
| **Uso de padrões arquiteturais** | **Sim**               | **O que faz:** Reconhece, sugere e implementa padrões arquiteturais.<br>**Como faz:** Analisa código existente para identificar padrões, sugere refatorações e implementa novos padrões.<br>**Exemplo:** Detecta que projeto usa Repository Pattern e mantém consistência ao adicionar novos módulos. Sugere refatoração para Singleton quando identifica múltiplas instâncias de classe de configuração.<br>**Limitação:** Aplicação de padrões é reativa. Não cria architecture decision records (ADRs) formais ou documenta rationale das escolhas arquiteturais. |

---

## 4.3. Design de Software

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| **Sugestão/uso de padrões de projeto** | **Sim**           | **O que faz:** Identifica oportunidades e implementa Design Patterns.<br>**Como faz:** Analisa código e sugere padrões apropriados (Strategy, Factory, Observer, Decorator, etc.) via refatoração assistida.<br>**Exemplo:** Ao identificar múltiplos condicionais para processar pagamentos, sugere "refatorar usando Strategy Pattern" e implementa automaticamente as classes necessárias.<br>**Limitação:** Foco em padrões clássicos do GoF. Pode não reconhecer ou sugerir padrões específicos de domínio ou padrões emergentes em frameworks modernos. |

---

## 4.4. Construção de Software

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| **Geração de código** | **Sim (Excelente)** | **O que faz:** Gera código através de múltiplas interfaces.<br>**Como faz:** <br>• **Tab (Autocomplete):** Predições inline multi-linha em tempo real<br>• **Cmd+K:** Edições direcionadas por linguagem natural<br>• **Composer/Agent:** Criação de features completas multi-arquivo<br>**Exemplo:** Comando "criar endpoint REST para gerenciar produtos com validação de estoque" gera models, schemas, routes, validações e tratamento de erros em arquivos separados.<br>**Limitação:** Código gerado pode ser verboso. Requer revisão humana para otimização e conformidade com padrões específicos da empresa. |
| **Refatoração**       | **Sim**           | **O que faz:** Refatora código para melhorar legibilidade, performance e manutenibilidade.<br>**Como faz:** Comandos diretos como "refatorar esta função para usar list comprehension" ou "extrair esta lógica em uma classe separada".<br>**Exemplo:** Transforma função procedural de 100 linhas em classes com responsabilidades únicas, aplicando SOLID principles.<br>**Limitação:** Refatorações complexas que envolvem mudanças em banco de dados ou APIs externas requerem supervisão cuidadosa para evitar breaking changes. |
| **Detecção de bugs**  | **Sim**           | **O que faz:** Identifica bugs em tempo real e sugere correções.<br>**Como faz:** <br>• **AI Linter:** Análise estática contínua<br>• **Auto-debug:** Lê stack traces e sugere fixes<br>• **Terminal Integration:** Captura erros de execução e propõe soluções<br>**Exemplo:** Ao executar código com erro "AttributeError: 'NoneType' object has no attribute 'id'", analisa contexto e sugere adicionar validação de None antes do acesso.<br>**Limitação:** Detecta bugs sintáticos e lógicos óbvios. Bugs complexos de concorrência, memory leaks ou race conditions podem não ser identificados. |

---

## 4.5. Teste de Software

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| **Geração de testes (unit., integração, aceitação)** | **Sim**          | **O que faz:** Gera testes automaticamente baseados no código.<br>**Como faz:** Analisa função/classe e cria suite de testes cobrindo casos felizes, edge cases e exceções.<br>**Exemplo:** Para função `calculate_discount(price, percentage)`, gera testes para: valores normais, porcentagem 0%, porcentagem > 100%, valores negativos, None inputs.<br>**Limitação:** Testes de aceitação (end-to-end) são mais limitados, pois requerem conhecimento de fluxos de negócio completos. Foco maior em testes unitários e de integração. |
| **Execução de testes automatizados**             | **Sim (Parcial)**     | **O que faz:** Executa testes em background para validar correções.<br>**Como faz:** Através do "Shadow Workspace", roda testes antes de sugerir mudanças ao usuário.<br>**Exemplo:** Ao corrigir um bug, valida que a correção não quebra testes existentes antes de aplicar.<br>**Limitação:** Execução é local e limitada a testes rápidos (unit/integration). Não substitui pipelines de CI/CD completos com testes E2E em ambientes de staging. |

---

## 4.6. Operações de Software

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| **CI/CD**                         | **Não**               | **Limitação:** Não atua como servidor de CI/CD (runner). Pode gerar scripts de configuração (GitHub Actions, GitLab CI, Jenkinsfile), mas não executa pipelines ou realiza deploys automaticamente. A orquestração permanece com ferramentas dedicadas. |
| **Automação**                     | **Sim (Local apenas)** | **O que faz:** Automatiza tarefas de desenvolvimento local.<br>**Como faz:** Gera e executa scripts shell/Python via terminal integrado.<br>**Exemplo:** Pode criar script para "automatizar setup de ambiente de desenvolvimento" ou "gerar dados de teste".<br>**Limitação:** Automação é local e sob demanda. Não gerencia processos de background autônomos, cron jobs em servidores ou automação de infraestrutura cloud. |
| **Monitoramento**                 | **Não**               | **Limitação:** Não possui telemetria, dashboards ou alertas para monitorar saúde de software em produção. Não coleta métricas de execução (uptime, latência, error rate). Útil apenas para depuração reativa de logs estáticos fornecidos pelo usuário. |
| **Documentação técnica automatizada** | **Sim**           | **O que faz:** Gera documentação técnica de código e APIs.<br>**Como faz:** Analisa codebase e cria docstrings, READMEs, documentação de APIs (OpenAPI/Swagger), diagramas de fluxo.<br>**Exemplo:** Pode gerar automaticamente README.md completo com instalação, uso, arquitetura e exemplos baseado no código existente.<br>**Limitação:** Documentação é baseada em código. Não captura conhecimento tácito ou decisões de design não explícitas no código. |

---

## 4.7. Manutenção de Software

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| **Correções automatizadas** | **Sim**           | **O que faz:** Bug fixing assistido por IA.<br>**Como faz:** <br>• Lê stack traces do terminal<br>• Analisa contexto do erro<br>• Sugere ou aplica correção automaticamente<br>• Valida correção com testes<br>**Exemplo:** Feature "Add to Chat" no terminal permite copiar erro e receber correção contextualizada. Para erro de import circular, sugere reorganização de módulos com código completo.<br>**Limitação:** Eficaz para bugs sintáticos e lógicos simples. Bugs de design arquitetural ou performance complexa requerem intervenção humana significativa. |

---

## 4.8. Gerenciamento de Projeto de Software

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| **Planejamento**                    | **Fraco**             | **O que faz:** Auxilia apenas em planejamento técnico imediato.<br>**Como faz:** Decomposição de tarefas técnicas através de "Plan Mode" ou chat ("Como devo implementar sistema de notificações?").<br>**Exemplo:** Pode sugerir "1. Criar modelo Notification, 2. Implementar service de envio, 3. Criar endpoints REST, 4. Adicionar testes".<br>**Limitação:** Não realiza planejamento estratégico de projeto, gestão de backlog, criação de WBS/EAP, ou estimativas de cronograma. |
| **Execução**                        | **Sim**               | **O que faz:** Atua como co-piloto na execução técnica.<br>**Como faz:** Acelera implementação de tarefas através de geração de código, refatoração e testes.<br>**Exemplo:** Transforma task "implementar autenticação OAuth" em código funcional em minutos ao invés de horas.<br>**Limitação:** Execução é limitada à codificação. Não gerencia reuniões, comunicação de stakeholders ou entregáveis não-técnicos. |
| **Controle**                        | **Não**               | **Limitação:** Não monitora progresso do projeto, marcos, desvios de escopo ou performance da equipe. Não gera relatórios de status ou dashboards de projeto. |
| **Encerramento**                    | **Não**               | **Limitação:** Não oferece suporte a processos de encerramento formal, aceitação de entregáveis, lições aprendidas ou arquivamento administrativo. |
| **Gestão de riscos**                | **Fraco**             | **O que faz:** Identifica riscos técnicos apenas.<br>**Como faz:** Análise de vulnerabilidades de segurança (SQL injection, XSS) e bugs críticos no código.<br>**Exemplo:** Alerta sobre uso de inputs não sanitizados ou dependências com vulnerabilidades conhecidas.<br>**Limitação:** Não avalia riscos de negócio, organizacionais, financeiros ou de mercado. Análise limitada ao código-fonte. |
| **Estimativas (tempo, custo, esforço)** | **Não**           | **Limitação:** Não possui noções de tempo, deadlines ou calendário. Não realiza estimativas de esforço (Story Points, horas) ou custos de desenvolvimento. Completamente desconectado de gestão financeira e orçamentação. |
| **Medição**                         | **Não**               | **Limitação:** Não coleta métricas de processo (Lead Time, Cycle Time, Velocity, densidade de defeitos). Não gera relatórios de produtividade ou qualidade do processo. Atua apenas como editor, não como ferramenta de BI ou analytics. |

---
<-- Inalterado -->
# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

- [x] **Tipo de interface:** Chat, autocomplete, comandos ou agente?
  - **Resposta:** Múltiplas interfaces integradas:
    - **Chat:** Conversação sobre código com histórico
    - **Autocomplete (Tab):** Predições inline em tempo real
    - **Comandos (Cmd+K):** Edições direcionadas com linguagem natural
    - **Agent/Composer:** Agente autônomo para tarefas complexas multi-arquivo

- [x] **Integração:** Funciona dentro do editor/IDE ou é ferramenta separada?
  - **Resposta:** Funciona **DENTRO** do editor (fork do VS Code). Integração nativa e profunda com o ambiente de desenvolvimento. Suporta todas as extensões do VS Code.

- [x] **Facilidade inicial:** Consegui usar nos primeiros 5 minutos sem tutoriais?
  - **Resposta:** **SIM**. Configuração extremamente simples:
    - Download e instalação em menos de 2 minutos
    - Importação automática de configurações do VS Code
    - Funcionamento imediato no plano free
    - UI familiar para usuários de VS Code

## 2. Contexto do Projeto

- [x] **Lê arquivos automaticamente:** Preciso colar código ou ela vê o projeto?
  - **Resposta:** **SIM**. Sistema sofisticado de indexação:
    - Indexação automática do codebase completo via embeddings
    - Modelo de embedding proprietário para entendimento profundo
    - Busca semântica em toda a base de código
    - @mentions para incluir arquivos/pastas específicas no contexto
    - Contexto pode chegar a 1M tokens (Claude Sonnet 4) ou 200k tokens (GPT-4)

- [x] **Entende a stack:** Detecta linguagens/frameworks ou preciso explicar tudo?
  - **Resposta:** **SIM**, detecção automática e inteligente:
    - Detecta linguagens, frameworks, dependências automaticamente
    - Analisa package.json, requirements.txt, etc.
    - Adapta sugestões ao estilo e convenções do projeto
    - .cursorrules permite definir regras customizadas do projeto

- [x] **Múltiplas linguagens:** Funciona bem com mais de uma linguagem?
  - **Resposta:** **SIM**. Suporte excelente para:
    - Linguagens mainstream: Python, JavaScript, TypeScript, Java, C++, Go, Rust, etc.
    - Web: HTML, CSS, React, Vue, Angular, etc.
    - Mobile: Swift, Kotlin, Flutter, React Native
    - Funciona bem em projetos polyglot (múltiplas linguagens simultaneamente)

## 3. Modo de Trabalho

- [x] **Nível de autonomia:** Só sugere ou também modifica arquivos sozinha?
  - **Resposta:** Escalável - "Autonomy Slider":
    - **Tab:** Apenas sugere completions (baixa autonomia)
    - **Cmd+K:** Edita onde você indica (média autonomia)
    - **Agent:** Alta autonomia - navega, edita múltiplos arquivos, executa testes, corrige erros
    - **Background Agent:** Trabalha em paralelo enquanto você codifica

- [x] **Controle do usuário:** Posso revisar antes de aceitar mudanças?
  - **Resposta:** **SIM**, controle granular em todos os níveis:
    - **Tab:** Accept/reject com Tab/Esc
    - **Cmd+K:** Preview antes de aplicar
    - **Agent:** Mostra diffs, permite accept/reject por arquivo
    - **Modo 'Privacy':** Código nunca sai da máquina (desativa algumas features)

- [x] **Escopo das ações:** Mexe em 1 arquivo por vez ou vários simultaneamente?
  - **Resposta:** Totalmente escalável:
    - **Single line:** Tab autocomplete
    - **Single file:** Cmd+K, Chat
    - **Multi-file:** Agent/Composer (pode editar dezenas de arquivos em uma operação)
    - **Codebase-wide:** Refactorings globais, migrations

## 4. Capacidades Observadas

- [x] **Completude:** Gera blocos inteiros de código ou apenas linhas soltas?
  - **Resposta:** Gera código completo e contextual:
    - **Tab:** Prediz 10x+ linhas em sequência (não apenas próxima linha)
    - Sugere funções completas, classes, módulos
    - **Agent:** Pode criar features completas multi-arquivo
    - **Modelo Fusion:** 25%+ melhoria em edições difíceis, 10x+ trechos mais longos

- [x] **Explicação:** Possui funcionalidade dedicada para explicar código (botão/comando)?
  - **Resposta:** **SIM**, múltiplas formas:
    - **Chat:** Explica qualquer código selecionado
    - Documentação on-the-fly durante desenvolvimento
    - Pode gerar documentação técnica completa
    - Explains reasoning quando usa Extended Thinking

- [x] **Correção:** Possui comandos explícitos de /fix ou "Debug this"?
  - **Resposta:** **SIM**, debugging integrado:
    - Detecta erros em tempo real (AI Linter)
    - Sugere fixes imediatos para erros
    - **Agent:** Lê mensagens de erro, executa testes, corrige automaticamente
    - **GitHub Integration:** Code review automatizado (Bugbot)
    - Busca na web por soluções quando necessário

- [x] **Referências:** Cita de onde tirou a informação (fontes) ou gera sem referência?
  - **Resposta:** Cita fontes quando relevante:
    - Pode buscar na web e citar documentação oficial
    - @docs permite adicionar documentação custom como contexto
    - Geralmente não cita para código comum, mas pode explicar origem de padrões

## 5. Limitações Importantes

- [x] **Vinculada a plataforma específica:** Força uso de serviços (ex: AWS, Azure)?
  - **Resposta:** **NÃO**. Completamente independente:
    - Não força uso de serviços cloud específicos
    - Funciona com qualquer stack/framework
    - BYOK permite usar APIs próprias
    - Pode trabalhar offline (com limitações)

- [x] **Restrições de linguagem/stack:** Tem tecnologias que não suporta bem?
  - **Resposta:** Poucas restrições:
    - Excelente para linguagens mainstream
    - Bom para linguagens menos comuns (depende do modelo escolhido)
    - Pode ter limitações em linguagens muito obscuras ou domain-specific
    - DSLs podem requerer instruções customizadas via .cursorrules

- [x] **Curva de aprendizado:** Precisa de muito treino pra usar direito?
  - **Resposta:** Baixa a moderada:
    - **Básico:** Imediato (se já usa VS Code)
    - **Intermediário:** ~1-2 semanas para dominar todas as features
    - **Avançado:** Otimização de prompts, .cursorrules, integração com CI/CD
    - **Trade-off:** Ganhos de produtividade compensam investimento em aprendizado

--- 
