# 1. Identificação da Ferramenta

| Item                            | Descrição                                                                      |
|---------------------------------|--------------------------------------------------------------------------------|
| *Nome da ferramenta*          |Codeium (Plugin)                / Windsurf (IDE AI-Native).                                                               |
| *Fabricante / Comunidade*     |                              Codeium (antiga Exafunction).                                                 |
| *Site oficial / documentação* | https://codeium.com                                                / https://windsurf.com                                  |
| *Tipo de ferramenta*          | IDE Híbrida com Agentes (Windsurf) e Assistente de Código (Plugin).
| *Licença / acesso*            | Híbrido (Plugin VsCode é gratuito, mas IA é fechada (SaaS))        .                                      |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                | Descrição                                                    |
|-------------------------------------|--------------------------------------------------------------|
| *Tipo de IA Generativa*           | Híbrido: LLM Multimodal + Agentes (Cascade)          |
| *Nome do Modelo*                  |**Agentes(Cascade):** SWE-1.5 - Claude Sonnet 4.5 - Claude Sonnet 4.5 (Thinking) - Claude Opus 4.5 - Claude Opus 4.5 (Thinking) - Claude Haiku 4.5 - Gemini 3.0 Pro (low) - Gemini 3.0 Pro (high) - GPT-5.2 (No Reasoning) - GPT-5.2 (Low Reasoning) - GPT-5.2 (Medium Reasoning) - GPT-5.2 (High Reasoning) - GPT-5.2 (Extra High Reasoning) - GPT-5.2 (No Reasoning Fast) - GPT-5.2 (Low Reasoning Fast) - GPT-5.2 (Medium Reasoning Fast) - GPT-5.2 (High Reasoning Fast) - GPT-5.2 (Extra High Reasoning Fast) - GPT-5.1 (No Reasoning) - GPT-5.1 (Low Reasoning) - GPT-5.1 (Medium Reasoning) - GPT-5.1 (High Reasoning) - GPT-5.1 (No Reasoning Fast) - GPT-5.1 (Low Reasoning Fast) - GPT-5.1 (Medium Reasoning Fast) - GPT-5.1 (High Reasoning Fast) - GPT-5.1-Codex - GPT-5.1-Codex Mini - GPT-5 (Low Reasoning) - GPT-5 (Medium Reasoning) - GPT-5 (High Reasoning) - GPT-5-Codex - SWE-1 - Gemini 2.5 Pro - Claude Opus 4.1 - Claude Opus 4.1 (Thinking) - xAI Grok Code Fast - Kimi K2 - Qwen3-Coder Fast - Qwen3-Coder - o3 - o3 (high reasoning) - Claude 3.7 Sonnet - Claude 3.7 Sonnet (Thinking) - Claude Sonnet 4 - Claude Sonnet 4 (Thinking) - gpt-oss 120B (Medium) - GPT-4o - GPT-4.1 - Claude 3.5 Sonnet - Claude 4 Opus - Claude 4 Opus (Thinking) - DeepSeek-V3-0324 - DeepSeek-R1 **Autocomplete:** Codeium Proprietary Model.|
| *Versão*                          | Cascade 2.0 / SWE 1.5                                                             |
| *Tamanho (nº de parâmetros)*      | Não disponível.|
| *Acesso*                          | API Comercial (SaaS) ou Enterprise Self-Hosted (Binário fechado)
| *Suporte a Fine-tuning*           | Sim (Limitado a contexto/RAG na versão Enterprise; não treina pesos).
| *Suporte a RAG*                   | Sim                                .        |
| *Métodos de prompting suportados* | CoT, ReAct, Self-Refine e Tool Use.
| *Ferramentas adicionais*          | Integração MCP, Super-tether, DeepWiki.    |

---

# 3. Contexto de Execução

| Item                                  | Descrição                               |
|---------------------------------------|-----------------------------------------|
| *Onde roda?*                        |Híbrido: Cliente Local + Inferência em Nuvem (SaaS) ou Cluster Local (Enterprise).|
| *Infraestrutura utilizada no teste* | Cliente: PC/Notebook padrão (CPU convencional). Backend: Cluster SaaS proprietário (GPUs otimizadas para baixa latência).   |
| *Custos (quando aplicável)*         | Gratuito para indivíduos; Licença por usuário para times (SaaS); Enterprise (Custom) |

---

# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

- [ ] Tipo de interface: Chat, autocomplete, comandos e Agente autônomo (Cascade).
- [ ] Integração: Funciona dentro do editor/IDE e/ou como ferramenta separada.
- [ ] Facilidade inicial: Sim, sem dificuldades.

## 2. Contexto do Projeto

- [ ] Lê arquivos automaticamente: Sim, compreendendo não apenas o contexto local (arquivo local), mas também o contexto global (repositório inteiro).
- [ ] Entende a stack: Sim, detecta linguagens e frameworks automaticamente.
- [ ] Múltiplas linguagens: Funciona bem para múltiplas linguages.

## 3. Modo de Trabalho

- [ ] Nível de autonomia: Sugere e é capaz de modificar arquivos sozinha (Via Cascade).
- [ ] Controle do usuário: Sim, solicita um aceite antes de aplicar as mudanças.
- [ ] Escopo das ações: Mexe em vários arquivos simultaneamente (Via Cascade).

## 4. Capacidades Observadas

- [ ] Completude: Capaz de gerar um bloco inteiro de código (funções / classes).
- [ ] Explicação: Possui um chat integrado para explicações.
- [ ] Correção: Sim, possui comandos /fix para correções.
- [ ] Referências: Cita os arquivos lidos na resposta do chat.

## 5. Limitações Importantes

- [ ] Vinculada a plataforma específica: Não.
- [ ] Restrições de linguagem/stack: Falha em tipagem avançada de Python e na lógica de resolução de problemas complexos em C++. Além disso, o Codeium é uma black-box (isto significa que as operações internas do Codeium são inacessíveis para o usuário final), o que nos impossibilita de realizar a testagem proposta no OE3.
- [ ] Curva de aprendizado: Baixa para uso.