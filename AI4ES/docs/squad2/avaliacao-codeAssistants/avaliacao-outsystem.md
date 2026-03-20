# 1. Identificação da Ferramenta

| Item                            | Descrição                                                                      |
|---------------------------------|--------------------------------------------------------------------------------|
| *Nome da ferramenta*          |       OutSystems Mentor                                                                         |
| *Fabricante / Comunidade*     |          OutSystems                                                                       |
| *Site oficial / documentação* |      [Platform Overview - Mentor](https://www.outsystems.com/low-code-platform/mentor-ai-app-generation/) / [Documentation - Build apps with AI](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/build_apps_with_ai/)                                                                          |
| *Tipo de ferramenta*          | Recurso de geração/refino de aplicações por IA dentro da plataforma low-code OutSystems Developer Cloud (ODC).  | 
| *Licença / acesso*            | Comercial. Acesso via conta/licença/trial.                                            |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                | Descrição                                                    |
|-------------------------------------|--------------------------------------------------------------|
| *Tipo de IA Generativa*           | LLM (interpretação de linguagem natural) + arquitetura “agentic AI” (orquestração de agentes) aplicada à geração/refino de apps.                         |
| *Nome do Modelo*                  | Não divulgado. |
| *Versão*                          | Não divulgado.                                                            |
| *Tamanho (nº de parâmetros)*      | Não divulgado                                                |
| *Acesso*                          | API Privada/Gerenciada (o usuário não acessa o modelo diretamente, interage via IDE/Portal)                          |
| *Suporte a Fine-tuning*           | Não                     |
| *Suporte a RAG*                   | Não exposto/ não configurável pelo usuário no Mentor (no escopo do teste).                                                      |
| *Métodos de prompting suportados* | Prompting em Linguagem Natural (Chat), Upload de Arquivos de Requisitos (PDF/Docx)                            |
| *Ferramentas adicionais*          | Fora do escopo do teste: AI Agent Builder (para criar seus próprios agentes), AI Mentor Studio (Dashboard de Dívida Técnica).    |

---

# 3. Contexto de Execução

| Item                                  | Descrição                               |
|---------------------------------------|-----------------------------------------|
| *Onde roda?*                        | Cloud (OutSystems Developer Cloud – ODC).                 |
| *Infraestrutura utilizada no teste* | Ambiente SaaS gerenciado pela OutSystems (ODC).    |
| *Custos (quando aplicável)*         | Modelo baseado em subscrição anual, sob cotação. Edição Pessoal é gratuita (limitada a 100 usuários internos). |

---

# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

- [x] Tipo de interface: Chat, autocomplete, comandos ou agente?
    - Híbrida. Possui Chat/Agente (Mentor) para gerar apps do zero a partir de prompts/arquivos , Comandos Visuais e Dashboards (AI Mentor Studio) para análise de qualidade.
   
- [x] Integração: Funciona dentro do editor/IDE ou é ferramenta separada?
    - Integrado dentro da versãoo web.
    
- [x] Facilidade inicial: Consegui usar nos primeiros 5 minutos sem tutoriais?
    - Sim. Para a função gerar um app do zero com o Mentor AI, a barreira é baixa,  bastanto descrever o app que deseja. Entretanto, não é tão intuitivo quanto às alterações via IA. Para desenvolvimento profundo (lógica complexa), exige aprendizado da plataforma visual.

## 2. Contexto do Projeto

- [x] Lê arquivos automaticamente: Preciso colar código ou ela vê o projeto?
    - O Mentor consegue ler documentos de requisitos (PDF, Word) para gerar a aplicação inicial. O AI Mentor Studio lê automaticamente todos os módulos do ambiente (factory) para análise.
- [x] Entende a stack: Detecta linguagens/frameworks ou preciso explicar tudo?
    -Ele é especializado na stack proprietária da OutSystems. Ele "conhece" todas as tabelas, ações e APIs disponíveis no seu ambiente (Data Fabric) e usa isso para sugerir conexões.
- [ ] Múltiplas linguagens: Funciona bem com mais de uma linguagem?
    - Ele suporta a geração de SQL, mas não é uma ferramenta de propósito geral para escrever Python/Java.

## 3. Modo de Trabalho

- [x] Nível de autonomia: Só sugere ou também modifica arquivos sozinha?
    - **Alta Autonomia**. Ele não apenas sugere alterações, mas cria o banco de dados, as telas, a lógica de segurança e os fluxos de trabalho inteiros e publica a aplicação.
- [ ] Controle do usuário: Posso revisar antes de aceitar mudanças?
    - Não há revisão do usuário. Ao selecionar adicionar alteração, ele já realiza a modificação.
- [x] Escopo das ações: Mexe em 1 arquivo por vez ou vários simultaneamente?
    - **Vários**. Diferente de assistentes de código comuns, o Mentor cria/altera múltiplas camadas ao mesmo tempo, criando tabelas no banco de dados, gerando APIs de back-end e criando telas de front-end em uma única execução.

## 4. Capacidades Observadas

- [x] Completude: Gera blocos inteiros de código ou apenas linhas soltas?
    - Blocos completos/Apps inteiros. Gera aplicações funcionais "Full-Stack" (Interface + Dados + Lógica)
- [ ] Explicação: Possui funcionalidade dedicada para explicar código (botão/comando)?
    - Não possui explicações.
- [x] Correção: Possui comandos explícitos de /fix ou "Debug this"?
    - Sim (Via AI Mentor Studio). Ele identifica padrões de erro (Performance, Segurança, Manutenibilidade) e oferece sugestões de correção. Para alguns padrões simples, existe "Auto-fix". A arquitetura agêntica também se "auto-corrige" durante a geração para garantir que o código compile.
- [ ] Referências: Cita de onde tirou a informação (fontes) ou gera sem referência?
    - Não aplicável.

## 5. Limitações Importantes

- [x] Vinculada a plataforma específica: Força uso de serviços (ex: AWS, Azure)?
    - Sim. O OutSystems Mentor é exclusivo para gerar aplicações na plataforma OutSystems. O código gerado depende do runtime da plataforma.
- [x] Restrições de linguagem/stack: Tem tecnologias que não suporta bem?
    - Focado exclusivamente em desenvolvimento Web/Mobile moderno e Cloud-Native. Não é adequado para scripts de sistema.
- [x] Curva de aprendizado: Precisa de muito treino pra usar direito?
    - Média. Usar o chat para gerar o app é trivial. No entanto, para manter, refatorar e evoluir o que a IA criou, é necessário conhecimento técnico de desenvolvimento OutSystems.
