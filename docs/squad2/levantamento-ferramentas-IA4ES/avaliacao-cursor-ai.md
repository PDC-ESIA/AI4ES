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

# 5. Qualidade das Respostas

| Critério                            | Avaliação | Observações |
| ----------------------------------- | --------- | ----------- |
| **Precisão**                        | ⭐⭐⭐⭐     | **Alta na Construção e Testes:** Código gerado é funcional e compilável na maioria dos casos. Shadow Workspace valida implementações antes de sugerir, reduzindo erros. **Moderada em Arquitetura:** Sugestões arquiteturais são baseadas em padrões estabelecidos, mas podem não capturar nuances de contexto de negócio específico. |
| **Profundidade técnica**            | ⭐⭐⭐⭐     | **Excelente em padrões de código:** Reconhece e aplica Design Patterns (GoF), SOLID principles, padrões arquiteturais (MVC, Clean Architecture). **Limitada em aspectos avançados:** Não aborda arquiteturas distribuídas complexas (event sourcing, CQRS), otimização de performance em escala ou design de sistemas massivamente concorrentes. |
| **Contextualização no código/problema** | ⭐⭐⭐⭐⭐ | **Excepcional:** RAG com indexação semântica do codebase permite compreensão profunda do contexto. Conecta requisitos (comentários, documentação) à implementação (código) e testes. Analisa impacto de mudanças em múltiplos arquivos. Mantém consistência com estilo e convenções do projeto existente. |
| **Clareza**                         | ⭐⭐⭐⭐⭐   | **Muito clara:** Explicações em linguagem natural acessível. Documentação gerada é bem estruturada. Consegue traduzir conceitos técnicos complexos para diferentes níveis de audiência. Extended Thinking explica raciocínio quando necessário. |
| **Aderência às melhores práticas**  | ⭐⭐⭐      | **Boa em desenvolvimento:** Sugere refatorações, aplicação de padrões, código limpo. Detecta code smells. **Fraca em DevOps/Gestão:** Não promove práticas de CI/CD, monitoramento, observabilidade. Não considera aspectos de deployment, rollback ou operações em produção. |
| **Consistência entre respostas**    | ⭐⭐⭐⭐     | **Alta:** Mecanismos de Self-Refine e validação em background (linters, type checkers) garantem consistência. Mantém estilo do código ao longo de múltiplas interações. Ocasionalmente pode sugerir abordagens diferentes para o mesmo problema se contexto mudar. |
| **Ocorrência de alucinações**       | **Baixa** | **Mitigado por validação técnica:** Program-of-Thought (PoT) executa código mentalmente, Shadow Workspace testa implementações. **Alucinações ocorrem principalmente em:** (1) Bibliotecas/APIs muito recentes ou obscuras, (2) Dependências não instaladas, (3) Configurações específicas de ambiente não documentadas no projeto. |

---

# 6. Experimentos Realizados

## Descrição das tarefas testadas

**Tarefa principal:** Criar módulo de API REST completo para gerenciamento de Usuários (CRUD) usando:
- Python com FastAPI e SQLAlchemy
- Validação de e-mail e senha forte
- Autenticação JWT (inferida do projeto existente)
- Testes unitários com cobertura >80%
- Documentação automática

**Tarefas complementares:**
- Refatoração de código legado (função procedural de 150 linhas)
- Debugging de erro de importação circular
- Geração de testes para módulo existente sem cobertura

---

## Resultados quantitativos

### Tarefa 1: CRUD de Usuários (desenvolvimento do zero)

| Métrica | Com Cursor AI | Sem IA | Ganho |
|---------|---------------|--------|-------|
| **Tempo total** | 8 minutos | 45 minutos | **5.6x mais rápido** |
| **Erros durante desenvolvimento** | 1 (import não instalado) | 3-5 (typos, imports, validação) | **3-5x menos erros** |
| **Qualidade do código** | Alta (PEP8, patterns) | Variável (depende de fadiga) | **Consistência garantida** |
| **Cobertura de testes** | 92% (happy path + edge cases) | ~40% (só happy path) | **2.3x maior cobertura** |
| **Documentação** | Completa (docstrings + README) | Geralmente ausente | **Economiza 15-20min** |
| **Arquivos criados** | 6 (models, schemas, routes, tests, config, README) | 3-4 (sem testes/README) | **Projeto mais completo** |

### Tarefa 2: Refatoração de código legado

| Métrica | Com Cursor AI | Sem IA | Ganho |
|---------|---------------|--------|-------|
| **Tempo** | 3 minutos | 20 minutos | **6.7x mais rápido** |
| **Bugs introduzidos** | 0 (validação com testes) | 1-2 (quebra compatibilidade) | **Zero regressão** |
| **Complexidade ciclomática** | 15 → 4 | 15 → 7-8 | **Melhor qualidade** |

### Tarefa 3: Geração de testes para módulo sem cobertura

| Métrica | Com Cursor AI | Sem IA | Ganho |
|---------|---------------|--------|-------|
| **Tempo** | 2 minutos | 15 minutos | **7.5x mais rápido** |
| **Cobertura alcançada** | 88% | 60-70% | **~25% mais cobertura** |
| **Edge cases cobertos** | 12 | 4-6 | **2-3x mais cenários** |

---

# 7. Pontos Fortes e Fracos da Ferramenta

## Pontos fortes

### 1. Redução da Carga Cognitiva na Manutenção

- Gestão de conhecimento de projetos legados
- Documentação automática (docstrings, READMEs)
- Explicações de fluxos complexos em linguagem natural
- Acelera onboarding de novos desenvolvedores

### 2. Antecipação da Validação (Shift-Left Testing)

- Valida viabilidade técnica em background (Shadow Workspace)
- Gera e executa testes para validar correções instantaneamente
- Move verificação para momento da construção
- Reduz custos de correção de bugs

### 3. Consistência Arquitetural Automatizada

- Atua como "revisor de código" contextual
- Sugere refatorações estruturais
- Reconhece e implementa padrões (MVC, Singleton, Factory)
- Garante aderência a normas técnicas

### 4. Análise de Impacto de Mudanças

- Mitiga risco de efeitos colaterais em engenharia de requisitos
- Modo Composer analisa impacto em múltiplos arquivos
- Garante propagação correta de alterações

### 5. Múltiplas Interfaces de Interação

- **Tab:** Autocomplete inteligente multi-linha
- **Cmd+K:** Edições direcionadas por linguagem natural
- **Chat:** Conversação contextual sobre código
- **Agent/Composer:** Tarefas complexas multi-arquivo

---

## Limitações

### 1. Desconexão com o Valor de Negócio

- Não prioriza baseado em ROI ou urgência
- Não gerencia backlog de User Stories
- Executa tarefas técnicas sem avaliar importância estratégica

### 2. Ausência de Métricas de Processo

- Não coleta Lead Time, Cycle Time, Velocity
- Não gera relatórios de produtividade
- "Caixa preta" para gerentes de engenharia

### 3. Inexistência de Gestão de Projetos

- Não estima prazos, custos ou esforço
- Sem cronograma ou caminho crítico
- Desconectado de gestão financeira e orçamentação

### 4. Limitação Operacional (DevOps)

- Não executa pipelines de CI/CD
- Não realiza deploys em produção
- Sem telemetria ou monitoramento em tempo real

### 5. Abstração Visual Limitada

- Não cria diagramas UML ou C4
- Arquitetura expressa apenas em código
- Dificulta comunicação com stakeholders não-técnicos

### 6. Colaboração Single-Agent

- Opera com único assistente
- Não possui arquitetura de enxame (swarm)
- Limitação para tarefas que requerem especialização paralela

---

# 8. Riscos, Custos e Considerações de Uso

## Riscos

### 1. Risco de Gestão (Cegueira Temporal)

- Sem calendário, cronograma ou deadlines
- Não gerencia caminho crítico
- Time pode focar em execução técnica e perder visão de prazos

### 2. Limitação na Análise de Risco

- Análise restrita a riscos técnicos
- Não avalia riscos de negócio, organizacionais ou financeiros
- Limitada a código-fonte

### 3. Privacidade e Processamento Remoto

- Inferência pesada ocorre na Cloud (US-based)
- Privacy Mode não retém código, mas processamento é remoto
- Uso 100% local possível apenas via configuração manual (BYOK + Ollama)

### 4. Dependência de Vendor

- Lock-in potencial após adaptação
- Migração para outro assistente pode ser custosa
- Dependência de disponibilidade da API

### 5. Ausência de Processos de Encerramento

- Sem suporte a encerramento formal
- Não auxilia em aceitação de entregáveis
- Sem arquivamento administrativo

---

## Custos

### Modelos de Licenciamento (SaaS)

| Plano | Custo | Características |
|-------|-------|-----------------|
| **Free** | $0/mês | Requisições lentas ilimitadas (fila), 2000 completions/mês |
| **Pro** | $20/mês | Tab ilimitado, $20 créditos API, ±225 req Sonnet 4 |
| **Pro Plus** | $60/mês | $70 créditos API (3.5x Pro), ±675 req Sonnet 4 |
| **Ultra** | $200/mês | $400 créditos API (20x Pro), ±4500 req Sonnet 4 |
| **Business** | $40/usuário/mês | 500 req incluídas, SSO, Privacy Mode, Admin |

### Infraestrutura Híbrida

- **Cloud:** GPUs para inferência pesada (custos inclusos nos planos)
- **Local:** CPU/GPU do desenvolvedor para indexação e modelo preditivo leve
- **Overhead:** ~500MB storage, 4GB+ RAM recomendado

### Custos Adicionais

- Uso além dos créditos: $0.04/requisição ou preço API do provedor
- Modelos premium podem consumir 2+ requisições por chamada
- Necessário monitoramento ativo para controlar gastos

---

## Considerações de Uso

### Escopo de Atuação

**O que Cursor É:**

- Editor de código superdotado
- Assistente de desenvolvimento individual
- Acelerador de execução técnica

**O que Cursor NÃO É:**

- Gerente de projetos
- Operador de infraestrutura
- Ferramenta de BI ou analytics

### Automação (Local vs. Servidor)

- Automação local: Geração e execução de scripts no terminal
- **Não gerencia:** Processos de background, cron jobs, infraestrutura cloud

### Papel no DevOps (Geração vs. Execução)

- **Gera:** Scripts de configuração (IaC, GitHub Actions, Jenkinsfile)
- **Não executa:** Pipelines, deploys, orquestração
- Ferramentas dedicadas permanecem necessárias (Jenkins, GitHub Actions)

### Monitoramento e Métricas

- **Não possui:** Telemetria, dashboards, alertas de saúde
- **Não coleta:** Métricas de processo (Lead Time, densidade de defeitos)
- Serve apenas para depuração reativa de logs fornecidos

### Planejamento (Técnico vs. Estratégico)

- **Auxilia em:** Decomposição de tarefas técnicas (Plan Mode)
- **Não realiza:** Planejamento estratégico, gestão de backlog, WBS/EAP

### Modelos de IA Envolvidos

- **Fronteira:** Claude Sonnet 4.5, GPT-5, Gemini 3 Pro, Grok Code
- **Proprietários:** Cursor Tab (Fusion), cursor-small
- **Customização:** BYOK permite usar modelos próprios via API

---

# 9. Conclusão Geral da Análise

## Adequação da Ferramenta

### Casos de Uso Ideais (Alta adequação)

**Construção e Codificação**

- Geração inline, completação multi-arquivo, refatoração via linguagem natural
- Papel: "Copilot++" que acelera desenvolvimento dramaticamente

**Manutenção e Evolução**

- Compreensão de código legado
- Documentação automática e explicação de fluxos complexos
- Correção de bugs assistida com contexto

**Verificação e Validação (Nível Unitário)**

- Shift-Left Testing
- Geração e validação de testes unitários/integração localmente
- Execução pré-commit para validação

**Detalhamento Técnico de Requisitos**

- Transformação de especificações textuais em código
- Análise de impacto de mudanças em múltiplos arquivos

---

### Casos para Evitar (Inadequada)

**Gerenciamento de Projetos**

- Estimativas de prazos, custos, esforço
- Controle de cronograma e caminho crítico
- "Cegueira" temporal e financeira

**Orquestração de DevOps**

- Execução de pipelines de CI/CD
- Deploys em ambientes de produção
- Não substitui Jenkins, GitHub Actions, GitLab CI

**Monitoramento de Produção**

- Observabilidade (SRE)
- Coleta de métricas de execução, logs de saúde, telemetria
- Inadequada para operações em tempo real

**Priorização de Negócio**

- Definição de "o que fazer primeiro" (backlog)
- Não compreende ROI ou urgência de negócio
- Decisões estratégicas requerem intervenção humana

---

## Maturidade Técnica

**Estágio:** State-of-the-Art (Fronteira) no nicho de Coding Assistants

**Diferenciais tecnológicos:**

- **Shadow Workspace:** Valida viabilidade em background
- **RAG Local:** Indexação vetorial de repositório completo
- **Modelos de ponta:** Claude Sonnet 4.5, GPT-5 + proprietários otimizados
- **Fine-tuning especializado:** Prevê "próxima edição" vs "próxima palavra"
- **Agentes transparentes:** ReAct no terminal, Program-of-Thought

**Comparação com concorrentes:**

- **vs GitHub Copilot:** Melhor contexto de codebase, multi-modelo, agentes mais avançados
- **vs Claude Code (CLI):** Interface gráfica completa, múltiplos modos de interação
- **vs Codeium/Tabnine:** Capacidades agênticas superiores, contexto até 1M tokens

---

## Recomendação para Adoção

### Vale a pena?

**Sim, com alinhamento estratégico aos objetivos OE1 e OE5.**

O Cursor AI se posiciona como ferramenta adequada para as fases iniciais do projeto (ME1 e parte da ME3), mas não deve ser tratado como solução completa para os objetivos de pesquisa e desenvolvimento propostos.

**Altamente adequado para:**

- **OE1 (Avaliação de Assistentes Comerciais):** Representa benchmark importante entre assistentes de código comerciais. Arquitetura multi-modelo e capacidades agênticas avançadas oferecem insights valiosos para o design do portfólio de agentes especializados.
- **OE5 (Prototipação e Integração):** Serve como referência arquitetural para integração de LLMs em sistemas reais. Modo Agent/Composer demonstra padrões de interação multi-arquivo aplicáveis ao TACO.

**Parcialmente adequado para:**

- **OE4 (Técnicas AI4SE):** Útil para aceleração da implementação de protótipos (TRL 4), mas não substitui a pesquisa fundamental em geração de testes, refatoração e engenharia de requisitos. Deve ser complementado com modelos open-source para garantir reprodutibilidade científica.

---

# 10. Referências e Links Consultados

## Documentação Oficial

- [Site oficial](https://cursor.com/)
- [Documentação completa](https://docs.cursor.com/)
- [Blog oficial com releases](https://cursor.com/blog)

## Features Principais

- [Composer 2.0 (Agente AI Nativo)](https://cursor.com/blog/2-0)
- [Shadow Workspace](https://cursor.com/blog/shadow-workspace)
- [Codebase Indexing (RAG)](https://cursor.com/docs/context/codebase-indexing)

## Pricing e Governança

- [Planos e Pricing](https://cursor.com/docs/account/pricing)
- [Privacidade e Governança](https://cursor.com/docs/enterprise/privacy-and-data-governance)

## Integrações

- [Integração com Claude 3.5 Sonnet](https://medium.com/towards-agi/how-to-use-cursor-ai-with-claude-3-5-sonnet-step-by-step-guide-4e1bbdd7bd65)

---

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
