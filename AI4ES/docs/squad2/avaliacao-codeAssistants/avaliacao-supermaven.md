## 1. Identificação da Ferramenta

| Item | Descrição |
| :--- | :--- |
| **Nome da ferramenta** | Supermaven |
| **Fabricante / Comunidade** | Supermaven Inc. (Fundada por Jacob Jackson, criador do Tabnine) |
| **Site oficial / documentação** | [supermaven.com](https://supermaven.com) |
| **Tipo de ferramenta** | Plugin de IDE / Assistente de Código de Baixa Latência |
| **Licença / acesso** | Híbrido: Freemium (Plano Gratuito e Plano Pro Comercial) |

## 2. Informações do Modelo de IA Utilizado

| Item | Descrição |
| :--- | :--- |
| **Tipo de IA Generativa** | LLM (Large Language Model) com arquitetura de atenção otimizada. |
| **Nome do Modelo** | **Babble** (Modelo proprietário para autocomplete) + Claude 3.5 Sonnet/GPT-4o (para Chat). |
| **Versão** | SaaS (Rolling release, atualizações contínuas via servidor). |
| **Tamanho (nº de parâmetros)** | Não divulgado (Proprietário, focado em inferência de baixíssima latência). |
| **Acesso** | API Fechada (Acessível apenas via plugin oficial). |
| **Suporte a Fine-tuning** | **Não** (no sentido tradicional). Realiza aprendizado em tempo real ("In-context learning") usando a janela de 1 milhão de tokens. |
| **Suporte a RAG** | **Não necessita.** Substitui o RAG tradicional por *Long Context* (insere o código todo no prompt devido à janela de 1M tokens). |
| **Métodos de prompting** | Infill (preenchimento de meio), Chat conversacional. |
| **Ferramentas adicionais** | Extensões para VS Code, JetBrains (IntelliJ, PyCharm, etc.) e Neovim. |

## 3. Contexto de Execução

| Item | Descrição |
| :--- | :--- |
| **Onde roda?** | **Cloud** (Processamento nos servidores da Supermaven). |
| **Infraestrutura utilizada** | GPU Clusters proprietários da Supermaven. |
| **Custos** | • **Free:** Gratuito (contexto alto, mas limitado).<br>• **Pro:** $10/mês (1 Milhão de tokens de contexto).<br>• **Team:** $10/usuário/mês (faturamento centralizado). |

---

## Checklist: Avaliação Inicial de Assistentes de Código

### 1. Entendimento Geral da Ferramenta
* **Tipo de interface:** Híbrido (Autocomplete "Ghost text" + Chat lateral).
* **Integração:** Funciona dentro do editor/IDE (Plugin nativo).
* **Facilidade inicial:** **Alta.** Instalação simples, login e uso imediato sem configurações complexas.

### 2. Contexto do Projeto
* **Lê arquivos automaticamente:** **Sim.** Carrega arquivos recentes e relevantes automaticamente na janela de 1 milhão de tokens.
* **Entende a stack:** **Sim.** Detecta automaticamente baseado na estrutura e extensões dos arquivos.
* **Múltiplas linguagens:** **Sim.** Suporte robusto para linguagens web e de backend populares (JS, TS, Python, Go, Rust, Java).

### 3. Modo de Trabalho
* **Nível de autonomia:** **Assistivo.** Sugere trechos (autocompletar) e responde a dúvidas, mas não aplica mudanças em massa sem supervisão.
* **Controle do usuário:** **Total.** Necessário pressionar `Tab` para aceitar sugestões ou copiar código do chat.
* **Escopo das ações:** Focado no arquivo ativo + conhecimento contextual profundo dos outros arquivos.

### 4. Capacidades Observadas
* **Completude:** Gera blocos inteiros de código e funções completas com alta velocidade.
* **Explicação:** **Sim.** Funcionalidade disponível através da janela de Chat.
* **Correção:** **Sim.** Via Chat (ex: colar o erro ou pedir para analisar o código selecionado).
* **Referências:** **Implícitas.** O modelo sabe de onde tirou a informação (devido ao contexto carregado), mas raramente gera citações formais.

### 5. Limitações Importantes
* **Vinculada a plataforma específica:** **Não.** Agnostic de nuvem (não força AWS ou Azure), mas requer IDE compatível (VS Code, JetBrains, Neovim).
* **Restrições de linguagem/stack:** Performance inferior em linguagens legadas com poucos dados públicos de treinamento.
* **Curva de aprendizado:** **Baixa.** A ferramenta é projetada para ser "invisível" e rápida.
* **Privacidade:** Código é enviado para a nuvem da Supermaven. Empresas com *compliance* rígido (bancos/governo) devem avaliar os termos de retenção de dados do plano Team/Pro.