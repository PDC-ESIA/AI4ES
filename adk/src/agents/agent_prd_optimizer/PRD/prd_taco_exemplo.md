# PRD — Repositório TACO IDE
**Versão:** 0.1  
**Origem:** Requisitos
**Destino:** Agente otimizador de PRD 
**Status:** Bruto — aguardando fracionamento 

---

## 1. Visão Geral do Produto

O TACO IDE é um ambiente de desenvolvimento integrado voltado ao ensino de programação. Seu diferencial é um sistema de chat educacional embutido, alimentado por agentes inteligentes que auxiliam estudantes em tempo real durante a escrita de código. Os agentes devem ser capazes de responder dúvidas, sugerir correções, explicar conceitos e registrar o progresso do aluno.

---

## 2. Módulo: Autenticação de Usuários

O sistema deve suportar dois perfis de usuário: Aluno e Professor. O cadastro será feito via e-mail e senha. Deve haver validação de e-mail com link de confirmação. O login deve gerar um token JWT com expiração de 8 horas. O token deve ser renovável via refresh token. Professores têm permissões adicionais: criar turmas, adicionar alunos e visualizar relatórios de progresso. O sistema deve bloquear o acesso após 5 tentativas de login falhas consecutivas por 15 minutos.

---

## 3. Módulo: Chat Educacional

O chat deve funcionar em tempo real usando WebSockets. Cada sessão de chat é vinculada a um exercício ou projeto aberto na IDE. O histórico de mensagens deve ser persistido no banco de dados com referência ao exercício. O agente de chat deve identificar automaticamente a linguagem de programação do contexto. Mensagens enviadas pelo aluno devem ser analisadas: se contiverem código, o agente deve avaliar possíveis erros antes de responder. O chat deve suportar formatação Markdown nas respostas do agente. O agente deve ter um modo "socrático": em vez de dar a resposta direta, faz perguntas guiadas para estimular o raciocínio do aluno. Limite de 4.000 tokens por sessão de chat ativa para controle de custos.

---

## 4. Módulo: Editor de Código (IDE Core)

Suporte inicial às linguagens: Python, JavaScript e HTML/CSS. O editor deve ter syntax highlighting, autocomplete básico e detecção de erros em tempo real (linting). Integração com o agente de chat: ao selecionar um trecho de código e clicar em "Explicar", o trecho é enviado automaticamente para o chat. Deve haver um botão "Executar" que roda o código em um sandbox isolado (sem acesso à rede). O resultado da execução (stdout/stderr) é exibido em um painel inferior. O editor deve salvar automaticamente o progresso a cada 30 segundos (autosave).

---

## 5. Módulo: Gerenciamento de Turmas

Professores podem criar turmas com nome, descrição e código de convite. Alunos entram na turma pelo código de convite. Cada turma tem uma lista de exercícios atribuídos pelo professor. O professor pode acompanhar em tempo real quais alunos estão ativos e em qual exercício estão trabalhando. Relatórios de progresso mostram: tempo gasto por exercício, número de interações com o agente e taxa de conclusão.

---

## 6. Módulo: Agente Supervisor (Orquestrador)

O Agente Supervisor é responsável por orquestrar os demais agentes do sistema. Ele recebe eventos da IDE (aluno abriu exercício, enviou mensagem, executou código) e decide qual subagente acionar. Deve implementar um mecanismo de fallback: se o subagente demorar mais de 10 segundos para responder, o Supervisor retorna uma mensagem padrão ao aluno. O Supervisor deve logar todas as decisões de roteamento em um arquivo de auditoria. Comunicação entre Supervisor e subagentes via ADK (Google Agent Development Kit).

---

## 7. Requisitos Não-Funcionais

- Latência máxima de resposta do agente de chat: 3 segundos (P95).
- O sistema deve suportar até 200 alunos simultâneos por instância.
- Banco de dados: PostgreSQL para dados persistentes, Redis para sessões e cache.
- Deploy inicial: ambiente local (on-premise) com Docker Compose.
- Logs estruturados em JSON para todas as operações dos agentes.
- Cobertura mínima de testes: 70% por módulo.

---

## 8. Integrações Externas

- LLM Provider: Mistral AI (mistral-small-latest para chat, mistral-large para avaliação de código).
- Sandbox de execução de código: Judge0 (self-hosted).
- Notificações por e-mail: SMTP configurável.

---

## 9. Restrições e Riscos

- O sistema NÃO deve armazenar o conteúdo das mensagens de chat em texto plano (criptografar em repouso).
- O sandbox de execução NÃO deve ter acesso à rede externa.
- Risco: complexidade do modo socrático — requer prompt engineering extenso e validação pedagógica.
- Risco: sincronização em tempo real com muitos alunos simultâneos pode gerar gargalos no WebSocket.
