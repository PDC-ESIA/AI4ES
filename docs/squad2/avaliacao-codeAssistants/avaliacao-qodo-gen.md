## 1. Identificação da Ferramenta

| Item | Descrição |
|---|---|
| **Nome da ferramenta** | Qodo Gen (anteriormente CodiumAI) |
| **Fabricante / Comunidade** | Qodo (CodiumAI) - Startup especializada em Integridade de Código e Testes Automatizados |
| **Site oficial / documentação** | Site: https://www.qodo.ai/ <br> Docs: https://docs.qodo.ai/ |
| **Tipo de ferramenta** | Assistente de Qualidade de Código & Geração de Testes (IDE Extension / Quality-First Agent) |
| **Licença / acesso** | **Freemium** <br> • *Developer (Grátis):* Uso individual ilimitado para geração de testes e chat. <br> • *Teams/Enterprise:* Pago (focado em PR reviews e governança). |

## 2. Informações do Modelo de IA Utilizado

| Item | Descrição |
|---|---|
| **Tipo de IA Generativa** | LLM Híbrido especializado em Lógica de Verificação e Segurança (Test-Driven LLM). |
| **Nome do Modelo / Versão / Tamanho / Acesso** | **Modelo:** TestGPT (Modelo proprietário *fine-tuned* sobre GPT-4 e outros SOTA). <br> **Versão:** Atualizada continuamente via SaaS (Plugin v7.x+). <br> **Acesso:** API Comercial (gerenciada pelo plugin). |
| **Suporte a Fine-tuning** | **Não (usuário final).** O modelo utiliza aprendizado em contexto (*In-Context Learning*) baseado no repositório local, mas não permite fine-tuning explícito de pesos pelo usuário. |
| **Suporte a RAG** | **Sim.** Utiliza RAG focado em comportamento (*Behavior-Oriented*). Analisa importações e definições de tipos para entender a lógica de negócio antes de sugerir testes. |
| **Métodos de prompting suportados** | • **Flow-Engineering:** Fluxo guiado (Análise -> Plano -> Código). <br> • **Chat Contextual:** Comandos `/improve`, `/fix`, `/test`. <br> • **Smart Chat:** Seleção automática de contexto via `@`. |
| **Ferramentas adicionais** | • **Behavior Analysis:** Descreve a lógica do código em linguagem natural. <br> • **Test Studio:** Interface gráfica para ativar/desativar casos de teste. <br> • **Auto-Fix:** Agente de correção de bugs com explicação. |

## 3. Contexto de Execução

| Item | Descrição |
|---|---|
| **Onde roda?** | **Híbrido.** Interface local no VS Code/JetBrains, mas o processamento pesado (inferência do LLM) ocorre na Nuvem da Qodo. |
| **Infraestrutura utilizada no teste** | **Local:** VS Code em Windows (CPU padrão). <br> **Nuvem:** Processamento remoto (SaaS), sem necessidade de GPU local. |
| **Custos (quando aplicável)** | **Gratuito** para o escopo do teste (Plano Developer Individual). |

---

## Checklist: Avaliação Inicial de Assistentes de Código

### 1. Entendimento Geral da Ferramenta
* **Tipo de interface:** Híbrida (Agente + GUI). Possui botões *CodeLens* ("Test this function") integrados ao editor, painel de Chat lateral e uma GUI dedicada ("Test Studio").
* **Integração:** Funciona **dentro** do editor (VS Code/JetBrains) como extensão nativa. Interage com terminal e árvore de arquivos.
* **Facilidade inicial:** **Alta.** A instalação é "Plug-and-Play". A detecção de funções testáveis é automática.

### 2. Contexto do Projeto
* **Lê arquivos automaticamente:** **Sim.** Demonstrou capacidade de ler múltiplos arquivos para resolver dependências (ex: mocks em C, imports em Python).
* **Entende a stack:** **Sim.** Detectou automaticamente bibliotecas padrão de Python (`logging`, `json`) e necessidade de compiladores em C (GCC).
* **Múltiplas linguagens:** **Sim.** Testado com sucesso em Python (Script ETL) e C (Algoritmos recursivos), mantendo qualidade em ambas.

### 3. Modo de Trabalho
* **Nível de autonomia:** **Alto (Agente).** Capaz de projetar e criar arquivos de teste completos do zero (`test_ex3.c`), incluindo *mocks*, sem intervenção linha-a-linha.
* **Controle do usuário:** **Total.** Permite revisar "Comportamentos" (*Behaviors*) e selecionar casos de teste antes da geração.
* **Escopo das ações:** **Arquivo/Módulo.** Foca na unidade sob teste, mas pode criar novos arquivos em pastas adjacentes.

### 4. Capacidades Observadas
* **Completude:** **Excepcional.** Código gerado pronto para produção (ex: ETL com tratamento de erros `try/except` e logs estruturados).
* **Explicação:** **Sim (Behavior Analysis).** Funcionalidade dedicada que traduz código para linguagem natural, detalhando fluxo e saídas.
* **Correção:** **Sim (`/fix`).** Identificou proativamente riscos de segurança (*Stack Overflow*) e sugeriu refatorações defensivas.
* **Referências:** Foca na lógica interna, referenciando linhas específicas do arquivo original.

### 5. Limitações Importantes
* **Vinculada a plataforma específica:** **Não.** Gera código padrão (Vanilla Python/C) agnóstico à nuvem.
* **Restrições de linguagem/stack:** Funcionalidades visuais (*Test Studio*) mais ricas em JS/Python do que em C/C++ (onde foca no Chat).
* **Curva de aprendizado:** **Baixa.** O fluxo guiado democratiza a criação de testes complexos.