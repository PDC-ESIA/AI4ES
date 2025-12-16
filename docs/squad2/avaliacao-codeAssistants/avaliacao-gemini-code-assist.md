# 1. Identificação da Ferramenta

| Item | Descrição |
|---|---|
| *Nome da ferramenta* | Gemini Code Assist |
| *Fabricante / Comunidade* | Google Cloud / Google LLC |
| *Site oficial / documentação* | codeassist.google (Individual) / cloud.google.com/products/gemini (Enterprise) |
| *Tipo de ferramenta* | AI-Powered Coding Assistant / Developer Productivity Platform |
| *Licença / acesso* | Comercial (Standard e Enterprise) com Tier Gratuito (Individual) |

---

# 2. Informações do Modelo de IA Utilizado

| Item | Descrição |
|---|---|
| *Tipo de IA Generativa* | LLM / multimodal (Natureza multimodal nativa)  |
| *Nome do Modelo* | Família Gemini : Gemini 1.5 Pro e Gemini 2.5 Flash/Lite  |
| *Versão* | Gemini 1.5 Pro (Raciocínio) e Gemini 2.5 Flash (Latência)  |
| *Tamanho (nº de parâmetros)* | Arquitetura Mixture-of-Experts (MoE) que permite eficiência mesmo com trilhões de parâmetros potenciais (para o 1.5 Pro)  |
| *Acesso* | API comercial (Google Cloud Vertex AI) |
| *Suporte a Fine-tuning* | Não. O Google **não** realiza *fine-tuning* dos pesos neurais com o código do cliente. |
| *Suporte a RAG* | Sim. Implementado via **Code Customization (RAG Enterprise)**. |
| *Métodos de prompting suportados* | Suporta raciocínio complexo via Gemini 1.5 Pro (que permite CoT). |
| *Ferramentas adicionais* | Gemini CLI, Integração nativa com BigQuery e Colab Enterprise. |

---

# 3. Contexto de Execução

| Item | Descrição |
|---|---|
| *Onde roda?* | Cloud (SaaS) – **Não existe modo offline**. |
| *Infraestrutura utilizada no teste* | APIs Cloud do Google, modelos otimizados para inferência de baixíssima latência (Gemini 2.5 Flash). |
| *Custos (Edição Enterprise Anual)* | $45,00 / usuário / mês. |
| *Dependência de Rede* | Dependência total da latência da rede (RTT) até o PoP do Google mais próximo. |
| *Controles de Segurança* | Utiliza **VPC Service Controls** e **IAM** para gestão de acesso. |

---

# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

- [x] **Tipo de interface: Chat, autocomplete, comandos ou agente?** Interface híbrida: *Autocomplete* (Flash), Chat Lateral (Pro), Comandos (`/explain`, `/fix`), e **Agent Mode** (para execução multi-passo).
- [x] **Integração: Funciona dentro do editor/IDE ou é ferramenta separada?** Funciona via extensões dentro dos IDEs (VS Code, JetBrains, Android Studio) e ambientes Cloud (Cloud Shell Editor).
- [ ] **Facilidade inicial: Consegui usar nos primeiros 5 minutos sem tutoriais?** *Variável*. A interface básica é intuitiva, mas o Agent Mode e a Code Customization (RAG) exigem configuração inicial e aprovação de planos.

## 2. Contexto do Projeto

- [x] **Lê arquivos automaticamente: Preciso colar código ou ela vê o projeto?** Vê o projeto. O modelo pode carregar repositórios inteiros e documentações extensas na **Janela de Contexto Estendida (1M tokens)**.
- [x] **Entende a stack: Detecta linguagens/frameworks ou preciso explicar tudo?** Detecta. Possui suporte verificado para Java, JavaScript, Python, C, C++, Go, C#, e mais de 20 outras linguagens.
- [x] **Múltiplas linguagens: Funciona bem com mais de uma linguagem?** Sim, com suporte Tier 1 para linguagens nucleares e suporte geral (*long tail*) para outras.

## 3. Modo de Trabalho

- [x] **Nível de autonomia: Só sugere ou também modifica arquivos sozinha?** Ambos. O **Agent Mode** permite raciocínio, planejamento e execução multi-passo, podendo editar múltiplos arquivos em uma única interação.
- [x] **Controle do usuário: Posso revisar antes de aceitar mudanças?** Sim. O Agente executa e apresenta um **Diff View consolidado** para revisão final e aprovação.
- [x] **Escopo das ações: Mexe em 1 arquivo por vez ou vários simultaneamente?** Vários simultaneamente no **Agent Mode**.

## 4. Capacidades Observadas

- [x] **Completude: Gera blocos inteiros de código ou apenas linhas soltas?** Gera blocos lógicos inteiros (*Smart Actions*) e o corpo inteiro de testes adaptados (*boilerplate*).
- [x] **Explicação: Possui funcionalidade dedicada para explicar código (botão/comando)?** Sim, via `/explain`. O Gemini 1.5 Pro é usado para essa tarefa.
- [x] **Correção: Possui comandos explícitos de /fix ou "Debug this"?** Sim, via `/fix`. Também é integrado com o terminal via **Gemini CLI**.
- [x] **Referências: Cita de onde tirou a informação (fontes) ou gera sem referência?** Sim. Exibe **Citações de Fonte** (URL e licença) no IDE para mitigar riscos de IP, caso o código corresponda *literalmente e extensivamente* a uma fonte conhecida.

## 5. Limitações Importantes

- [x] **Vinculada a plataforma específica: Força uso de serviços (ex: AWS, Azure)?** Focado no ecossistema **Google Cloud**, onde a integração com BigQuery e Colab gera o maior valor.
- [x] **Restrições de linguagem/stack: Tem tecnologias que não suporta bem?** A ausência de suporte explícito e robusto ao **Visual Studio clássico** (IDE roxo, focado em .NET *full framework*) é um ponto de atrito.
- [x] **Curva de aprendizado: Precisa de muito treino pra usar direito?** O *Agent Mode* e a *Code Customization* (RAG) exigem que o desenvolvedor entenda e aprove os planos de ação propostos pela IA.
- [x] **Dependência Online:** **Não existe modo offline**. O serviço cessa imediatamente se a conexão de rede cair.
- [x] **Segurança:** O uso da **versão Gratuita (Individual)** em ambiente corporativo deve ser bloqueado, pois a política padrão permite que o Google utilize esses dados para melhoria de produtos.