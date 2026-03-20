# 1. Identificação da Ferramenta
| Item                            | Descrição                                                                      |
|---------------------------------|--------------------------------------------------------------------------------|
| **Nome da ferramenta**          | Cursor AI                                                                      |
| **Fabricante / Comunidade**     | Anysphere Inc. (Fundada em 2022 por Michael Truell, Sualeh Asif, Arvid Lunnemark e Aman Sanger - ex-alunos do MIT) |
| **Site oficial / documentação** | [Site oficial](https://cursor.com/) & [Documentação](https://cursor.com/docs)             |
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
| **Custos (quando aplicável)**         | **Plano FREE ($0/mês):**<br>• Requisições lentas ilimitadas (com fila)<br>• Acesso limitado a modelos premium<br>• Tab autocomplete limitado (2000/mês)<br>**Plano PRO ($20/mês):**<br>• Tab: Ilimitado<br>• Modelo Auto: Ilimitado<br>• $20 em créditos de API (±225 requisições Sonnet 4, ±550 Gemini, ±500 GPT-5)<br>• Uso adicional: $0.04/requisição ou preço API do provedor<br>**Plano PRO PLUS ($60/mês):**<br>• $70 em créditos API (3.5x do Pro)<br>• ±675 Sonnet 4, ±1650 Gemini, ±1500 GPT-5<br>**Plano ULTRA ($200/mês):**<br>• $0 em créditos API (20x do Pro)<br>• ±4500 Sonnet 4, ±11000 Gemini, ±10000 GPT-5<br>• Acesso prioritário a novos recursos<br>• Sem caps de computação<br>**Plano BUSINESS/TEAMS ($60/usuário/mês):**<br>• 500 requisições incluídas/usuário (alguns modelos premium consomem 2+ requisições por chamada)<br>• SSO, Privacy Mode, Admin controls<br>• Analytics e relatórios |

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
    - **1 linha (Single line):** Tab autocomplete
    - **1 arquivo (Single file):** Cmd+K, Chat
    - **2+ arquivos (Multi-file):** Agent/Composer (pode editar dezenas de arquivos em uma operação)
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
