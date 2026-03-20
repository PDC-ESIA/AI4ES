# 1. Identificação da Ferramenta

| Item                            | Descrição                                                                      |
|---------------------------------|--------------------------------------------------------------------------------|
| *Nome da ferramenta* | Amazon Q Developer                                                             |
| *Fabricante / Comunidade* | Amazon Web Services (AWS)                                                      |
| *Site oficial / documentação* | https://aws.amazon.com/q/developer/                                            |
| *Tipo de ferramenta* | Assistente de código baseado em IA (Plugin de IDE e Agente de Software)        |
| *Licença / acesso* | Híbrido (Nível gratuito "Free Tier" e versão Profissional paga)                |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                | Descrição                                                       |
|-------------------------------------|-----------------------------------------------------------------|
| *Tipo de IA Generativa* | LLM (Large Language Model)                                      |
| *Nome do Modelo* | Família Claude 3 (Anthropic) otimizada pela AWS                 |
| *Versão* | Claude 3.5 Sonnet / Claude 3 Haiku (dependendo da tarefa)       |
| *Tamanho (nº de parâmetros)* | Não divulgado publicamente pela AWS                             |
| *Acesso* | API comercial via AWS Bedrock (interno) / Extensões de IDE      |
| *Suporte a Fine-tuning* | Sim (via personalização com dados do cliente na versão Pro)     |
| *Suporte a RAG* | Sim (Contexto local do repositório e bases de conhecimento)     |
| *Métodos de prompting suportados* | CoT, ReAct, Chat direto e Comandos de Slash (/fix, /test)       |
| *Ferramentas adicionais* | Extensões VSCode/JetBrains, AWS CLI, Console AWS                |

---

# 3. Contexto de Execução

| Item                                  | Descrição                               |
|---------------------------------------|-----------------------------------------|
| *Onde roda?* | Cloud (Processamento na AWS)            |
| *Infraestrutura utilizada no teste* | Serviço gerenciado via AWS Bedrock      |
| *Custos (quando aplicável)* | Gratuito (Free) ou US$ 19/mês (Pro)     |

---

# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

- [x] Tipo de interface: Chat lateral, autocomplete em linha e comandos de terminal.
- [x] Integração: Funciona integrado ao VS Code, JetBrains, Visual Studio, Eclipse e Console AWS.
- [x] Facilidade inicial: Interface intuitiva; exige apenas login com AWS Builder ID.

## 2. Contexto do Projeto

- [ ] Lê arquivos automaticamente: Não é automático, precisa digitar o comando @(pasta ou arquivo que deve ser lido).
- [x] Entende a stack: Detecta automaticamente a linguagem (Python, JS, Java, etc.) ao abrir o arquivo.
- [x] Múltiplas linguagens: Suporte robusto às principais linguagens de mercado.

## 3. Modo de Trabalho

- [x] Nível de autonomia: Atua como copiloto e agente (capaz de criar planos de implementação).
- [x] Controle do usuário: O usuário deve aceitar (Tab) ou revisar as sugestões do chat (as alterações de refatoração são diretas no código).
- [x] Escopo das ações: Na versão Pro, consegue realizar transformações em múltiplos arquivos (Agentic workflows).

## 4. Capacidades Observadas

- [x] Completude: Gera funções inteiras e até esqueletos de projetos completos.
- [x] Explicação: Possui comando dedicado para explicar trechos de código selecionados.
- [x] Correção: Possui recursos de segurança e debug integrados para sugerir correções.
- [x] Referências: Cita fontes de documentação oficial da AWS e repositórios públicos quando relevante.

## 5. Limitações Importantes

- [x] Vinculada a plataforma específica: Fortemente integrada ao ecossistema AWS.
- [ ] Restrições de linguagem/stack: Muito forte em Java/Python, mas pode variar em linguagens menos populares.
- [x] Curva de aprendizado: Baixa para uso básico, mas exige entender comandos @workspace para RAG avançado.
