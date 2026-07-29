# Relatório de Pesquisa — Ferramentas Open Source para Gaps de Tools e Workspace

## 1. Objetivo
Acelerar a evolução do ecossistema AI4ES/TACO por meio do reaproveitamento de ferramentas open source consolidadas, evitando o desenvolvimento de funcionalidades já disponíveis na comunidade. Este relatório estrutura os gaps identificados quando o ecossistema é comparado ao SOTA, avalia ferramentas OSS candidatas para cada gap segundo cinco critérios (aderência funcional, maturidade, facilidade de integração, compatibilidade com a arquitetura existente, custo de manutenção), e propõe o desenho de PoCs para as ferramentas selecionadas.

## 2. Glossário
- **SOTA**: State of The Art (Estado da Arte)
- **Gaps endereçáveis**: existem técnicas conhecidas, falta implementar
- **PoC**: Prova de Conceito
- **Aderência funcional**: o quanto a ferramenta resolve o gap diretamente, sem adaptação forçada
- **HITL**: Human-in-the-Loop — mecanismo de pausa da execução aguardando decisão humana
- **Tool Confirmation**: feature nativa do ADK (`require_confirmation` / `tool_context.request_confirmation`) para pausar uma tool call aguardando aprovação
- **DinD (Docker-in-Docker)**: container que hospeda seu próprio daemon Docker, usado por sandboxes self-hosted
- **microVM**: máquina virtual leve (ex: Firecracker), alternativa a containers como unidade de isolamento
- **Framework concorrente vs. lib incorporável**: ferramenta que substitui o orquestrador de agentes (ex: AutoAgent) vs. uma que se integra como componente dentro do orquestrador já existente (ex: semantic-router)

## 3. Gaps Consolidados (por frente)

### 3.1 Frente A — Execução/Workspace Isolado
- Ambiente de Execução Isolado e Aberto
- Workspace como ambiente docker-sandboxed com sistema de arquivos persistente e estado de execução
- Espaço de ações baseado em código executável em vez de chamadas JSON a tools predefinidas
- Comunicação com o sandbox por meio de um servidor de API REST
- Cria ponto de restauração do estado do filesystem do workspace antes de comandos de risco moderado (snapshot-rollback)
- Agente que clona e explora documentação e baixa quaisquer dependências

### 3.2 Frente B — Segurança/Governança de Execução
- Classificação de comandos do agente por nível de risco antes da execução

### 3.3 Frente C — Seleção e Design de Tools
- Seleção de tools por alinhamento de embeddings em vez de geração de nome do identificador
- Princípio WYSIWYG para prompts de tools — o que o agente vê no prompt é idêntico ao código Python real da interface
- Partir da query para construir as tools — não o inverso
- Refinamento de documentos de tools

### 3.4 Frente D — Tool Learning
- Tool learning como geração de código estruturado
- Algoritmo para o funcionamento da criação de tools em tempo de execução
- Estrutura que transforma autonomamente repositórios de código científico em ferramentas compatíveis com LLM

## 4. Ferramentas Avaliadas

### 4.1 Frente A
| Ferramenta | Gap(s) endereçado(s) | Link |
|---|---|---|
| Daytona | Workspace sandboxed, snapshot-rollback, comunicação REST, clonagem/exploração | https://github.com/daytonaio/daytona.git |
| OpenHands | Workspace sandboxed, código executável, REST, `security_risk` no schema | https://github.com/OpenHands/OpenHands.git |
| E2B | Ambiente de execução isolado (microVM/Firecracker) | https://github.com/e2b-dev/E2B.git|

### 4.2 Frente B
| Ferramenta | Gap(s) endereçado(s) | Link |
|---|---|---|
| ADK Tool Confirmation (nativo) | Classificação/pausa de risco via `require_confirmation` / `request_confirmation` | https://adk.dev/ |

### 4.3 Frente C
| Ferramenta | Gap(s) endereçado(s) | Link |
|---|---|---|
| semantic-router (Aurelio AI) | Seleção de tools por embeddings | https://github.com/aurelio-labs/semantic-router.git|
| vLLM Semantic Router *(monitorar)* | Roteamento semântico de **modelo**, não de **tool** — baixa aderência apesar do nome | https://github.com/vllm-project/semantic-router.git|

### 4.4 Frente D
| Ferramenta | Gap(s) endereçado(s) | Link |
|---|---|---|
| AutoAgent (HKUDS) | Tool learning + criação de tools em runtime, via geração de código controlada | https://github.com/HKUDS/AutoAgent.git|
| RepoAgent | Parcial: documentação estruturada de repositório (não tool em runtime) | https://github.com/OpenBMB/RepoAgent.git|

## 5. Análise Comparativa (rubrica de 5 critérios)

Escala: **Alto / Médio / Baixo**

### 5.1 Frente A
| Ferramenta | Aderência | Maturidade | Integração | ADK | Manutenção |
|---|---|---|---|---|---|
| Daytona | Alto | Médio | Alto (SDK testado) | **Alto** — extra oficial `[daytona]` | Baixo (Cloud) / Alto (self-hosted, DinD) |
| OpenHands | Alto (fonte de 5 práticas) | Alto (~70-80k estrelas, MIT core) | Médio (não inspecionado) | Médio — sem extra oficial | Baixo (core) — ressalva: nuvem/enterprise não-OSS |
| E2B | Médio-Alto | Alto (~12k estrelas, Apache-2.0) | Não testado | **Alto** — extra oficial `[e2b]` | Baixo (Cloud), self-host não verificado |

### 5.2 Frente B
| Ferramenta | Aderência | Maturidade | Integração | ADK | Manutenção |
|---|---|---|---|---|---|
| ADK Tool Confirmation | Alto (tool isolada); Baixo/Médio (multi-agente/A2A) | Baixo-Médio ("experimental") | Alto | Alto (nativo) | Baixo (mantido pelo Google) |

### 5.3 Frente C
| Ferramenta | Aderência | Maturidade | Integração | ADK | Manutenção |
|---|---|---|---|---|---|
| semantic-router (Aurelio AI) | Médio — exige curadoria de exemplos | Médio-Alto (~3.2k estrelas, MIT) | Não testado | Médio — lib standalone | Médio (equipe pequena) |
| vLLM Semantic Router | Baixo para este gap (foco é modelo, não tool) | Alto (backing Red Hat/vLLM) | Não avaliada | Não avaliada | Baixo (bem financiado) |

### 5.4 Frente D
| Ferramenta | Aderência | Maturidade | Integração | ADK | Manutenção |
|---|---|---|---|---|---|
| AutoAgent (HKUDS) | Alto — resolve diretamente | Média-Alta (~8-9k estrelas, HKU lab) | Não testada | **Baixo** — framework concorrente, não lib | Média (custo de coordenar 2 orquestradores) |
| RepoAgent | Baixo/Médio — pipeline batch, não tool runtime | Médio (~1k estrelas, atividade reduzida desde dez/2024) | Baixo — é CLI/hook | Baixo | Médio |

## 6. Justificativa da Seleção

### 6.1 Ferramentas selecionadas para PoC
- **ADK Tool Confirmation** — maior facilidade de integração do levantamento (nativa, zero dependência nova), aderência alta, custo de manutenção mínimo.
- **Daytona (Cloud)** — aderência validada via inspeção real do SDK, extra oficial no `google-adk`. Começar por Cloud antes de self-hosted.

### 6.2 Ferramentas descartadas (desta rodada de PoC)
- **OpenHands** — mantido como referência conceitual, mas sem extra oficial no ADK; integração manual via REST sem ganho claro sobre Daytona.
- **E2B** — descarte provisório, por menor profundidade de investigação (SDK não inspecionado); candidato a reavaliar.
- **semantic-router (Aurelio AI)** — custo de curadoria de exemplos maior que o tempo disponível para PoC enxuta.
- **vLLM Semantic Router** — resolve problema adjacente (modelo, não tool); manter em observação.
- **AutoAgent (HKUDS)** — **atualização em relação à conclusão anterior**: existe ferramenta madura e aderente. Descarte é por incompatibilidade arquitetural (framework concorrente ao ADK, não lib incorporável), não por ausência de opção.
- **RepoAgent** — resolve problema adjacente (documentação em lote, não tool de contexto em runtime).

## 7. Desenho da(s) PoC(s)

### 7.1 PoC 1 — ADK Tool Confirmation aplicado a `tool_criar_arquivo`
- **Escopo**: uma única tool de escrita, testada isoladamente com um agente ADK simples.
- **Critério de sucesso**: `security_risk="HIGH"` pausa via `request_confirmation`, retoma e escreve corretamente após aprovação; `LOW`/`MEDIUM` não aciona pausa.
- **Fora de escopo**: propagação multi-agente (`AgentTool`/A2A); demais tools do arquivo.

### 7.2 PoC 2 — Daytona Cloud como backend de uma tool de escrita
- **Escopo**: reimplementar `tool_criar_arquivo` usando `google-adk[daytona]` para escrever em sandbox remoto.
- **Critério de sucesso**: arquivo persiste entre chamadas na mesma sessão; autostop funciona sem erro.
- **Fora de escopo**: self-hosted; migração das demais 13 pastas do `AGENT_DIRS`; multi-tenant.

## 8. Recomendações de Adoção

| Ferramenta | Recomendação | Prazo |
|---|---|---|
| ADK Tool Confirmation | Adotar | Dias |
| Daytona (Cloud) | Adotar com ressalvas | Semanas |
| OpenHands | Não adotar — referência conceitual | — |
| E2B | Reavaliar depois | A definir |
| semantic-router (Aurelio AI) | Reavaliar depois | Longo prazo |
| vLLM Semantic Router | Não adotar — monitorar | — |
| AutoAgent (HKUDS) | Não adotar — incompatibilidade arquitetural | — |
| RepoAgent | Não adotar | — |

## 9. Próximos Passos
- Executar PoCs 1 e 2 (seção 7).
- Aprofundar pesquisa de E2B e semantic-router/Aurelio AI antes de decidir sobre elas.
- Reavaliar Frente D após construir a tool própria de contexto, comparando esforço vs. custo de adotar um framework como AutoAgent.
- Monitorar vLLM Semantic Router caso a feature de tool-catalog filtering amadureça.
