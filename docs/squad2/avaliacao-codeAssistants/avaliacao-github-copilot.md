# 1. Identificação da Ferramenta

| Item                            | Descrição                                                                      |
|---------------------------------|--------------------------------------------------------------------------------|
| *Nome da ferramenta*          | Github Copilot                                                                   |
| *Fabricante / Comunidade*     | GitHub                                                                           |
| *Site oficial / documentação* | https://github.com/features/copilot?locale=pt-BR                                 |
| *Tipo de ferramenta*          | Assistente de código / Plugin de IDE / Plataforma multimodal                     |
| *Licença / acesso*            | Comercial                                                                        |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                | Descrição                                                    |
|-------------------------------------|--------------------------------------------------------------|
| *Tipo de IA Generativa*           | Multimodal                                                     |
| *Nome do Modelo*                  | Claude Haiku 4.5, Claude Opus 4.5 (Preview), Claude Sonnet 4, Claude Sonnet 4.5, Gemini 2.5 Pro, Gemini 3 Pro (Preview), GPT-4.1, GPT-4o, GPT-5, GPT-5 mini, GPT-5-Codex (Preview), GPT-5.1 (Preview), GPT-5.1-Codex (Preview), GPT-5.1-Codex-Max (Preview), GPT-5.1-Codex-Mini (Preview), GPT-5.2 (Preview), Grok Code Fast 1, Raptor mini (Preview), dentre outros à escolha do usuário.                                           |
| *Versão*                          | 0.35.0                                                         |
| *Tamanho (nº de parâmetros)*      | Depende do modelo selecionado                                  |
| *Acesso*                          | Plugin Instalado no editor de código/IDE, site do GitHub, CLI  |
| *Suporte a Fine-tuning*           | Parcialmente                                                   |
| *Suporte a RAG*                   | Não                                                            |
| *Métodos de prompting suportados* | ???                                                            |
| *Ferramentas adicionais*          | ???                                                            |

---

# 3. Contexto de Execução

| Item                                  | Descrição                               |
|---------------------------------------|-----------------------------------------|
| *Onde roda?*                          | Cloud                                   |
| *Infraestrutura utilizada no teste*   | Plugin no VSCode                        |
| *Custos (quando aplicável)*           | USD 10 / mês                            |

---

# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

- [X] Tipo de interface: Chat, autocomplete, comandos ou agente?
- [X] Integração: Funciona dentro do editor/IDE ou é ferramenta separada?
- [X] Facilidade inicial: Consegui usar nos primeiros 5 minutos sem tutoriais?

## 2. Contexto do Projeto

- [X] Lê arquivos automaticamente: Preciso colar código ou ela vê o projeto? **Vê o projeto**
- [X] Entende a stack: Detecta linguagens/frameworks ou preciso explicar tudo? **Detecta automaticamente**
- [X] Múltiplas linguagens: Funciona bem com mais de uma linguagem?

## 3. Modo de Trabalho

- [X] Nível de autonomia: Só sugere ou também modifica arquivos sozinha? **Depende da forma que for utilizada**
- [X] Controle do usuário: Posso revisar antes de aceitar mudanças?
- [X] Escopo das ações: Mexe em 1 arquivo por vez ou vários simultaneamente? **Vários de forma simultânea**

## 4. Capacidades Observadas

- [X] Completude: Gera blocos inteiros de código ou apenas linhas soltas? **Blocos completos**
- [X] Explicação: Possui funcionalidade dedicada para explicar código (botão/comando)?
- [X] Correção: Possui comandos explícitos de /fix ou "Debug this"?
- [0] Referências: Cita de onde tirou a informação (fontes) ou gera sem referência?

## 5. Limitações Importantes

- [X] Vinculada a plataforma específica: Força uso de serviços (ex: AWS, Azure)? **GitHub**
- [0] Restrições de linguagem/stack: Tem tecnologias que não suporta bem? **Nenhuma informada até o momento**
- [0] Curva de aprendizado: Precisa de muito treino pra usar direito? **Uso fácil**
