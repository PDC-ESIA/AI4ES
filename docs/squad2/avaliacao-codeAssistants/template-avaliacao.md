# 1. Identificação da Ferramenta

| Item                            | Descrição                                                                      |
|---------------------------------|--------------------------------------------------------------------------------|
| *Nome da ferramenta*          |                                                                                |
| *Fabricante / Comunidade*     |                                                                                |
| *Site oficial / documentação* |                                                                                |
| *Tipo de ferramenta*          | (ex.: assistente de código, LLM geral, plataforma multimodal, plugin IDE etc.) |
| *Licença / acesso*            | (Comercial, open-source, híbrido)                                              |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                | Descrição                                                    |
|-------------------------------------|--------------------------------------------------------------|
| *Tipo de IA Generativa*           | LLM / multimodal / difusão / híbrido                         |
| *Nome do Modelo*                  | ex.: GPT-4.1, Claude 3.5, DeepSeek-Coder, CodeLlama-34B etc. |
| *Versão*                          |                                                              |
| *Tamanho (nº de parâmetros)*      | Se disponível                                                |
| *Acesso*                          | API comercial / Open-source / Local                          |
| *Suporte a Fine-tuning*           | Sim/Não + tipo (LoRA, Full FT, Adapters)                     |
| *Suporte a RAG*                   | Sim/Não                                                      |
| *Métodos de prompting suportados* | CoT, ReAct, PoT, Self-Refine etc.                            |
| *Ferramentas adicionais*          | LangChain, LangGraph, Ollama, Groq, extensões VSCode etc.    |

---

# 3. Contexto de Execução

| Item                                  | Descrição                               |
|---------------------------------------|-----------------------------------------|
| *Onde roda?*                        | Local / Cloud / Híbrido                 |
| *Infraestrutura utilizada no teste* | (GPU, CPU, RAM ou serviço utilizado)    |
| *Custos (quando aplicável)*         | Preço por token, por licença ou por uso |

---

# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

- [ ] Tipo de interface: Chat, autocomplete, comandos ou agente?
- [ ] Integração: Funciona dentro do editor/IDE ou é ferramenta separada?
- [ ] Facilidade inicial: Consegui usar nos primeiros 5 minutos sem tutoriais?

## 2. Contexto do Projeto

- [ ] Lê arquivos automaticamente: Preciso colar código ou ela vê o projeto?
- [ ] Entende a stack: Detecta linguagens/frameworks ou preciso explicar tudo?
- [ ] Múltiplas linguagens: Funciona bem com mais de uma linguagem?

## 3. Modo de Trabalho

- [ ] Nível de autonomia: Só sugere ou também modifica arquivos sozinha?
- [ ] Controle do usuário: Posso revisar antes de aceitar mudanças?
- [ ] Escopo das ações: Mexe em 1 arquivo por vez ou vários simultaneamente?

## 4. Capacidades Observadas

- [ ] Completude: Gera blocos inteiros de código ou apenas linhas soltas?
- [ ] Explicação: Possui funcionalidade dedicada para explicar código (botão/comando)?
- [ ] Correção: Possui comandos explícitos de /fix ou "Debug this"?
- [ ] Referências: Cita de onde tirou a informação (fontes) ou gera sem referência?

## 5. Limitações Importantes

- [ ] Vinculada a plataforma específica: Força uso de serviços (ex: AWS, Azure)?
- [ ] Restrições de linguagem/stack: Tem tecnologias que não suporta bem?
- [ ] Curva de aprendizado: Precisa de muito treino pra usar direito?
