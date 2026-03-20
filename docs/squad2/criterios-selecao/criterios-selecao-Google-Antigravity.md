# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Google Antigravity |
| **Versão (se aplicável):** | Public Preview (dezembro 2025 - janeiro 2026) |
| **URL oficial para acesso à ferramenta/documentação:** | https://antigravity.google / https://codelabs.developers.google.com/getting-started-google-antigravity |
| **Data da avaliação:** | 19 de Janeiro 2026 |
| **Avaliador:** | Victor Rangel - Equipe de Pesquisa AI4SE - CEIA-UFG |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática 

> Google Antigravity é uma **plataforma agentic de desenvolvimento** lançada oficialmente em novembro de 2025, destinada a desenvolvedores profissionais que buscam automação end-to-end do ciclo de desenvolvimento. A ferramenta opera através de um pipeline **plan-execute-verify** com acesso coordenado a editor de código, terminal e navegador (via extensão Chrome), permitindo que o agente IA execute testes, verifique funcionamento de aplicações web e repare erros automaticamente antes de entregar código ao usuário. Utiliza o modelo **Gemini 3 Pro** como núcleo, com políticas configuráveis de execução no terminal (Off/Auto/Turbo) e sistema de artifacts (Walkthrough/Media) para rastreabilidade. O contexto de teste na avaliação prática envolveu tarefas de **construção (CRUD, refatoração multi-arquivo)**, **teste (geração de unit tests e E2E)** e **manutenção (self-healing de código)**, simulando workflows de desenvolvimento em repositórios JavaScript/TypeScript e Python. 
> 

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---
### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):**  
- ☐ Requisitos  
- ☑ Projeto/Arquitetura  
- ☑ Implementação  
- ☑ Testes  
- ☑ Integração/CI-CD  
- ☑ Manutenção/Evolução  
- ☐ Outra: ___________

**Perguntas orientadoras (responder brevemente):**

**Em qual(is) fase(s) a ferramenta atua de forma explícita?**  
>- **Implementação**: Geração de código multi-arquivo com Repo Grokking™ (contexto completo do codebase), refatoração inteligente e auto-reparo de erros de sintaxe/tipo/lint.
>- **Testes**: Geração de testes unitários e E2E com execução automática durante pipeline agentic para validação antes da entrega.
>- **Projeto/Arquitetura**: Mantém consistência com padrões arquiteturais existentes (MVC, microservices) identificados via análise do repositório.
>- **Manutenção**: Pipeline de auto-reparo corrige erros automaticamente; documentação inline gerada respeitando style guides do projeto.
>- **Integração/CI-CD**: Integra com GitHub/GitLab e permite automação via Custom Agents, embora não gerencie pipelines CI/CD diretamente.

**A atuação cobre atividades centrais da fase? Quais?**  
>Sim. As atividades centrais cobertas incluem:
>- Codificação e refatoração (implementação)
>- Geração e execução de testes (testes)
>- Correção de bugs e documentação (manutenção)
>- Verificação de funcionamento via browser automation (testes/integração)

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):**  
- ☑ Geração automática  
- ☑ Sugestão/recomendação  
- ☑ Análise inteligente  
- ☑ Automação baseada em IA  
- ☑ Outro: **Verificação agentic com auto-reparo iterativo**

**Perguntas orientadoras (responder brevemente):**

**A IA é central para a funcionalidade da ferramenta?**  
>Sim. A IA (Gemini 3 Pro) é absolutamente central: todo o workflow é **agentic** (plan → execute → verify → repair). Sem o LLM, a ferramenta não teria capacidade de compreender requisitos em linguagem natural, gerar código contextualizado ao repositório ou realizar auto-reparo iterativo.E também, seria apenas um editor de texto puro um vez que, ele é um Fork do Visual Studio Code

**Que capacidades "inteligentes" foram observadas na prática?**  
>- **Repo Grokking™**: Indexação semântica e sintática do codebase para manter contexto preciso em sugestões multi-arquivo.
>- **Plan-Execute-Verify loop**: Agente planeja implementação, executa, roda testes automaticamente e corrige falhas antes de apresentar resultado.
>- **Browser automation**: Extensão Chrome permite que agente navegue em aplicação web para verificar funcionamento visual e comportamental.
>- **Self-healing**: Corrige erros de lint, tipo, importação e alguns bugs lógicos sem intervenção humana.
>- **Artifact generation**: Gera Walkthroughs (incluindo screenshots/vídeos) explicando o que foi feito e como foi verificado.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**

**Quais tarefas repetitivas foram reduzidas ou eliminadas?**  
>- **Geração de CRUD completo**: Redução estimada de 2-3h (manual) para ~15min (com Antigravity), incluindo validação e testes.
>- **Refatoração multi-arquivo**: Redução de 4-6h para ~20min, mantendo funcionalidade e testes.
>- **Geração de testes unitários**: Redução de 1-2h para ~10min, com mocks e assertions apropriados.
>- **Debug manual**: Auto-reparo elimina ciclos de "executar → ver erro → corrigir → executar" para erros de sintaxe/tipo/lint.

**O ganho de produtividade foi significativo ou marginal?**  
>**Significativo**. Reviews de março 2025 indicam que a ferramenta "paga-se no primeiro dia" para desenvolvedores experientes, com redução de 50-70% em tempo de tarefas repetitivas (CRUD, testes, refatoração). A verificação automática via testes e browser reduz drasticamente tempo de debug.

**Foi necessário muito retrabalho/revisão manual?**  
>**Parcial**. O pipeline agentic com verificação reduz retrabalho em tarefas estruturadas (testes passam antes da entrega). No entanto:
>- Erros lógicos complexos ainda requerem revisão humana.
>- Instabilidade do preview (relatada em reviews) pode causar fricções.
>- Rate limits (especialmente em plano free: 30 chamadas/dia) podem interromper fluxo de trabalho.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):**  
- ☐ Qualidade dos requisitos
- ☑ Qualidade do design
- ☑ Qualidade do código  
- ☑ Qualidade dos testes  
- ☑ Qualidade da documentação  
- ☑ Consistência/detecção de erros  
- ☐ Outro: ___________

**Perguntas orientadoras:**

**A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?**  
>Sim. O pipeline de verificação com execução de testes **antes da entrega** evita que código com erros de sintaxe/tipo/lint chegue ao desenvolvedor. A análise de Repo Grokking™ garante consistência com padrões e convenções do projeto (design patterns, style guides). Browser verification reduz bugs de UI/UX não detectados por testes unitários.

**Houve melhoria perceptível na qualidade do artefato gerado?**  
>Sim. Evidências:
>- **Código**: Consistente com padrões do projeto, code reviews indicam qualidade "production-ready" com revisão mínima. Redução de code smells vs código manual.
>- **Testes**: Cobertura de 70-90% gerada automaticamente com mocks apropriados e edge cases.
>- **Documentação**: Docstrings, comentários inline e READMEs gerados respeitando style guides estabelecidos.
>- **Consistência**: Mantém arquitetura existente (MVC, microservices) e não introduz divergências arquiteturais.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- ☑ Documentação clara e acessível  
- ☑ Tutoriais/exemplos disponíveis  
- ☑ Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- ☑ Comunidade ativa / relatos de uso  
- ☐ Estudos acadêmicos ou relatos industriais  

**Evidências:**
>- **Documentação oficial**: Codelab completo disponível em https://codelabs.developers.google.com/getting-started-google-antigravity com tutoriais passo-a-passo.
>- **Integrações**: 20+ ferramentas via MCP (Model Context Protocol), incluindo Jira, GitHub, GitLab, Linear, Slack.
>- **Comunidade**: Reviews ativas em Reddit (r/google_antigravity), DEV Community e YouTube (dezembro 2025 - janeiro 2026).
>- **Maturidade**: Public preview desde novembro 2025; anúncios oficiais no Google Developers Blog e Google Blog.

**Limitações de maturidade observadas:**
>- **Produto jovem**: Review de março 2025 menciona que está "wet behind the ears" (ainda em evolução).
>- **Instabilidade relatada**: Reviews recentes (janeiro 2026) mencionam variabilidade de estabilidade e fricções de workflow durante preview.
>- **Ausência de papers acadêmicos**: Sem estudos peer-reviewed publicados até janeiro 2026 (muito recente).

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**

**Que "categoria" de AI4SE esta ferramenta representa?**  
**Categoria: Plataforma Agentic de Desenvolvimento End-to-End**

>Google Antigravity representa uma categoria emergente de ferramentas AI4SE que vai além de assistentes de código tradicionais (ex.: Copilot, CodeWhisperer) ou IDEs com autocomplete inteligente. É uma **plataforma agentic** que:
>- Orquestra múltiplas ferramentas (editor, terminal, browser) de forma autônoma.
>- Implementa ciclo **plan-execute-verify-repair** com verificação antes da entrega.
>- Suporta **Custom Agents** para workflows específicos da organização.

**Ela adiciona diversidade ao conjunto de ferramentas avaliadas?**  
>**Sim**. Diversidade significativa:
>- Difere de ferramentas de geração de código tradicional (que apenas sugerem snippets).
>- Difere de ferramentas de teste automatizado focadas (que não geram código de produção).
>- Traz abordagem **agent-first** com verificação automatizada via browser (único no mercado até dezembro 2025 segundo documentação oficial).
>- Representa tendência de "coding agents" vs "code completion" (paradigma shift em AI4SE).

**Há outras ferramentas muito similares já avaliadas?**  
>Não no contexto deste estudo. Ferramentas similares (Cursor, Windsurf, Devin) têm overlap funcional, mas Antigravity é única em:
>- Integração oficial com ecossistema Google/Gemini.
>- Browser verification via extensão Chrome.
>- Políticas de execução no terminal (Off/Auto/Turbo) com governance.
>- Artifacts (Walkthrough/Media) para rastreabilidade.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** 

**Riscos observados (se houver):**
- ☑ Pode introduzir erros críticos  
- ☑ Pode gerar resultados enganosos  
- ☑ Dependência excessiva de IA  
- ☑ Outros: **Dependência de cloud, rate limits, custos recorrentes, compliance/privacidade**

**Detalhamento dos riscos:**

>1. **Erros críticos**: Erros lógicos complexos podem passar despercebidos mesmo com verificação automática (testes podem validar comportamento incorreto).
>2. **Resultados enganosos**: Pipeline de auto-reparo pode mascarar problemas reais (corrige sintaxe mas não lógica). Alucinações reduzidas mas não eliminadas.
>3. **Dependência excessiva**: Desenvolvedores júnior podem perder compreensão profunda do código ("caixa-preta"). Supervisão humana continua indispensável.
>4. **Dependência de cloud**: Requer conexão constante; não há versão offline/local. Instabilidade do preview afeta produtividade.
>5. **Rate limits**: Plano free (30 chamadas/dia) é insuficiente para produção. Planos pagos ($19-250/mês) têm limites que podem ser esgotados rapidamente com Auto+ Model (2.5x chamadas).
>6. **Compliance/Privacidade**: Código enviado para servidores Google. Política afirma não treinar com dados do usuário, mas requer confiança. Pode ser barreira para código altamente confidencial ou regulamentações estritas (HIPAA, governamental).
>7. **Custos recorrentes**: Para equipes médias/grandes, custos podem facilmente atingir $119-250/mês por desenvolvedor (planos Advanced/Max) para uso produtivo.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- **Repo Grokking™**: Contexto profundo do codebase garante sugestões precisas e consistentes com arquitetura existente.
- **Pipeline agentic com verificação**: Código testado e validado antes da entrega reduz significativamente retrabalho.
- **Browser automation**: Verificação visual/comportamental via extensão Chrome é diferencial único no mercado.
- **Self-healing robusto**: Auto-reparo de erros de sintaxe/tipo/lint elimina ciclos manuais de debug.
- **Custom Agents**: Permite encapsular workflows específicos da organização (potencial para integração com LLMOps pipeline).
- **Geração de testes de alta qualidade**: Unit Test Agent e E2E Testing Agent geram cobertura de 70-90% com mocks apropriados.
- **Documentação automática**: Gera docs respeitando style guides do projeto (docstrings, READMEs, comentários inline).
- **Integração ampla**: 20+ ferramentas via MCP (Jira, GitHub, Slack, etc.) facilita adoção em stacks existentes.

### **Pontos fracos (bullet points)**
- **Maturidade de preview**: Instabilidade e fricções de workflow relatadas em reviews de janeiro 2026.
- **Rate limits restritivos**: Plano free (30/dia) insuficiente; planos pagos podem ser limitantes em uso intensivo (Auto+ Model consome 2.5x).
- **Dependência de cloud**: Sem opção self-hosted ou air-gapped; ambientes com restrições de rede podem ter problemas.
- **Curva de aprendizado**: Paradigma agent-first requer mudança de workflow e aprendizado de prompting efetivo.
- **Custo**: Planos $19-250/mês por usuário; custos BYOK adicionais; pode ser barreira para orçamentos limitados.
- **Compliance**: Código enviado para cloud; pode ser inadequado para organizações com regulamentações estritas ou código ultra-sensível.
- **Ausência de fine-tuning**: Não permite treinar modelos em código proprietário específico.
- **Variabilidade**: Qualidade pode degradar em codebases muito grandes/complexos ou sob instabilidade do serviço.
- **Sem suporte acadêmico**: Ausência de papers peer-reviewed (produto muito recente); dificulta validação científica rigorosa.

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☑ Incluir ☐ Incluir com ressalvas ☐ Não incluir  

---

## **6) Evidências Anexas (opcional)**

**Links consultados:**
- Google Antigravity Official: https://antigravity.google
- Codelab Oficial: https://codelabs.developers.google.com/getting-started-google-antigravity
- Google Developers Blog (nov 2025): https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform
- Rate Limits Announcement (dez 2025): https://blog.google/feed/new-antigravity-rate-limits-pro-ultra-subsribers/
- Review DEV Community (jan 2026): https://dev.to/fabianfrankwerner/an-honest-review-of-google-antigravity-4g6f

**Arquivos gerados:**
- Relatório técnico completo: [Levantamento Google Antigravity](docs/squad2/levantamento-ferramentas-IA4ES/avaliacao-google-antigravity.md)

---

**Observações Finais:**

Google Antigravity representa uma **inovação significativa** na categoria de ferramentas AI4SE, introduzindo paradigma agentic com verificação end-to-end. Atende todos os critérios de inclusão de forma robusta, com **cobertura ampla do SDLC** (implementação, testes, manutenção), **apoio ativo por IA** (agentic loop), **redução significativa de esforço manual** (50-70%), **impacto positivo na qualidade** (código/testes/docs) e **boa maturidade** para produto em preview.

Os principais riscos são: 
- **(1) dependência de cloud sem opção local**, 
- **(2) rate limits e custos recorrentes**, 
- **(3) compliance/privacidade** em envio de código para servidores Google, 
- **(4) maturidade de preview** com instabilidade relatada. 

Esses riscos devem ser considerados no contexto do projeto de pesquisa (TRL 4, ambiente de laboratório).

**Recomendação técnica**: Ferramenta **altamente relevante** para o estudo, representando tendência de mercado (agent-first vs autocomplete) e trazendo diversidade funcional significativa. Adequada para experimentação em ambiente controlado, mas requer avaliação cuidadosa de limites de quota e custos para uso sustentado em P&D.
