# 1. Identificação da Ferramenta

| Item                            | Descrição                                                                    |
|---------------------------------|------------------------------------------------------------------------------|
| *Nome da ferramenta*          | Blackbox AI                                                                    |
| *Fabricante / Comunidade*     | Blackbox AI Inc.                                                               |
| *Site oficial / documentação* | https://blackbox.ai / https://docs.blackbox.ai/                                |
| *Tipo de ferramenta*          | Assistente de código e LLM geral                                               |
| *Licença / acesso*            | Comercial                                                                      |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                | Descrição                                                                                                                                  |
|-------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| *Tipo de IA Generativa*           |  Multimodal e Multi-Agent                                                                                                                    |
| *Nome do Modelo*                  | Selecionável pelo usuário. Inclui modelos como Grok Code Fast Model (gratuito) e agentes especializados (Ex: Claude Code Agent, Codex Agent) |
| *Versão*                          | Depende do modelo selecionado                                                                                                                |
| *Tamanho (nº de parâmetros)*      | Depende do modelo selecionado                                                                                                                |
| *Acesso*                          | API comercial  e interface web                                                                                                               |
| *Suporte a Fine-tuning*           | Não                                                                                                                                          |
| *Suporte a RAG*                   | Não                                                                                                                                          |
| *Métodos de prompting suportados* | CoT implícito, prompting direto e instruções contextuais                                                                                     |
| *Ferramentas adicionais*          | Extensões VS Code, integração com IDEs                                                                                                       |

---

# 3. Contexto de Execução

| Item                                  | Descrição                                             |
|---------------------------------------|-------------------------------------------------------|
| *Onde roda?*                        | Híbrido                                                 |
| *Infraestrutura utilizada no teste* |  CPU, RAM                                               |
| *Custos (quando aplicável)*         | Inicial: R$ 27/mês; Pro: R$ 54/mês; Pro Plus: R$ 216/mês|

---

# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

- [ ] Tipo de interface: Chat e IDE.
- [ ] Integração: Funciona dentro do editor/IDE e pode ser ferramenta separada.
- [ ] Facilidade inicial: Sim, sem dificuldades.

## 2. Contexto do Projeto

- [ ] Lê arquivos automaticamente: Vê o projeto.
- [ ] Entende a stack: Detecta linguagens/frameworks.
- [ ] Múltiplas linguagens: Funciona bem com mais de uma linguagem.

## 3. Modo de Trabalho

- [ ] Nível de autonomia: Só sugere e também modifica arquivos sozinha.
- [ ] Controle do usuário: É possivel revisar antes de aceitar mudanças.
- [ ] Escopo das ações: Mexe em 1 arquivo.

## 4. Capacidades Observadas

- [ ] Completude: Gera blocos inteiros de código.
- [ ] Explicação: Possui funcionalidade dedicada para explicar código (botão/comando).
- [ ] Correção: Possui comandos explícitos de /fix ou "Debug this".
- [ ] Referências: Gera sem referência?

## 5. Limitações Importantes

- [ ] Vinculada a plataforma específica: Não força uso de serviços (ex: AWS, Azure).
- [ ] Restrições de linguagem/stack: Funciona com as principais linguagens. A plataforma Cloud tem restrição para repositórios Git vazios.
- [ ] Curva de aprendizado: Baixa para o uso do assistente. A curva é maior para a orquestração multi-agent e configurações avançadas de contexto.