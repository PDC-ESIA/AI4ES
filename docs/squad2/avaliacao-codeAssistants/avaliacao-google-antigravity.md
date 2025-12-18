# **1\. Identificação da Ferramenta**

| Item | Descrição |
| :---- | :---- |
| *Nome da ferramenta* | **Google Antigravity** |
| *Fabricante / Comunidade* | Google DeepMind / Google Labs |
| *Site oficial / documentação* | [antigravity.google](https://antigravity.google/) / [Docs](https://antigravity.google/docs/changes-sidebar?hl=pt-br) |
| *Tipo de ferramenta* | *Agentic IDE* / Plataforma *AI-First* (Fork do VS Code com Agentes) |
| *Licença / acesso* | Híbrido: Preview Gratuito (Atual). Planos Pro/Ultra/Enterprise futuros. |

# **2\. Informações do Modelo de IA Utilizado**

| Item | Descrição |
| :---- | :---- |
| *Tipo de IA Generativa* | LLM Multimodal (Texto \+ Código \+ Visão) |
| *Nome do Modelo* | **Primário:** Gemini 3 Pro (Lançado Nov/2025). **Raciocínio:** Gemini 3 Deep Think. **Opcionais:** Claude Sonnet 4.5, GPT-OSS. |
| *Versão* | Gemini 3 Pro / Deep Think |
| *Tamanho (nº de parâmetros)* | Não divulgado (Especulado \>1T / MoE) |
| *Acesso* | API Gerenciada Google (SaaS). Não permite *Bring Your Own Key* (BYOK). |
| *Suporte a Fine-tuning* | Não (No contexto da ferramenta). |
| *Suporte a RAG* | **Sim.** Sistema "Knowledge" integrado para memória de projeto. |
| *Métodos de prompting* | ReAct (Agentes), Self-Refine (Auto-correção) ,Chain-of-Thought. |
| *Ferramentas adicionais* | Browser Agent (Headless)  Terminal Seguro MCP (Model Context Protocol). |

# 

# **3\. Contexto de Execução**

| Item | Descrição |
| :---- | :---- |
| *Onde roda?* | **100% Cloud.** Código é enviado para servidores do Google. |
| *Infraestrutura utilizada* | Gerenciada pelo Google (TPUs). Acesso via Web App ou Desktop Electron. |
| *Custos* | **Preview:** Gratuito (Rate limits a cada 5h). **Futuro:** Assinatura Mensal (Pro/Ultra). |

# **Checklist: Avaliação Inicial de Assistentes de Código**

## **1\. Entendimento Geral da Ferramenta**

* \[x\] **Tipo de interface:** Híbrida (Chat, Autocomplete, Slash Commands e Agente Autônomo).  
* \[x\] **Integração:** IDE Completa (Fork do VS Code) com "Dual-View" (Editor \+ Gerente de Agentes).  
* \[ \] **Facilidade inicial:** **Parcial.** Exige curva de aprendizado (15 min) para entender o conceito de "Agent Manager".

## **2\. Contexto do Projeto**

* \[x\] **Lê arquivos automaticamente:** Sim (Indexação automática com janela de 1M tokens).  
* \[x\] **Entende a stack:** Sim (Detecção via package.json, requirements.txt).  
* \[x\] **Múltiplas linguagens:** Sim (Polyglot nativo: Python, JS/TS, Rust, Java, Go).

## **3\. Modo de Trabalho**

* \[x\] **Nível de autonomia:** **Alto.** Modifica múltiplos arquivos, roda terminal e cria branches Git sozinho.  
* \[x\] **Controle do usuário:** **Granular.** Políticas de *Allow/Deny List* para comandos e revisão de *Diffs*.  
* \[x\] **Escopo das ações:** **Multi-Arquivo.** Refatora dezenas de arquivos em uma única *task*.

## **4\. Capacidades Observadas**

* \[x\] **Completude:** Gera features *end-to-end* (Código \+ Teste \+ Doc).  
* \[x\] **Explicação:** Gera artefatos visuais ("Walkthrough") explicando as mudanças.  
* \[x\] **Correção:** **Self-Healing.** Loop automático (Executa \-\> Falha \-\> Corrige \-\> Re-executa).  
* \[ \] **Referências:** **Parcial.** Referência arquivos internos, mas não cita fontes externas (StackOverflow).

## **5\. Limitações Importantes**

* \[x\] **Vinculada a plataforma específica:** Requer Google Cloud para inferência (não roda offline).  
* \[ \] **Restrições de linguagem/stack:** **Leves.** Performance inferior em stacks legadas (Cobol) ou muito nichadas.  
* \[ \] **Curva de aprendizado:** **Média (5-10h).** Exige adaptação ao fluxo de "Gerente de Agentes" vs "Codificador".