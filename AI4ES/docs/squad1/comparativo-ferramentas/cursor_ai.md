#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          |           Cursor AI                                                                     |
| **Fabricante / Comunidade**     |                Anysphere Inc.                                                               |
| **Site oficial / documentação** |                  [Documentação Cursor AI](https://cursor.com/docs)                                                              |
| **Tipo de ferramenta**          | IDE AI-Native |
| **Licença / acesso**            | Híbrida, com modelos de acesso Freemium e Comercial.                                              |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | LLMs, mas com capacidades multimodais e uma arquitetura que pode ser considerada híbrida                         |
| **Nome do Modelo**                  | Cursor integra diversos LLM. Os principais são: Claude 4.5 Sonnet, GPT-5, Gemini 3 Pro, etc. O Cursor ainda conta com o Composer 1, um modelo nativo da plataforma |
| **Versão**                          | Modelos de fronteira sempre atualizados (ex: Claude 3.5, GPT-4o)                                                             |
| **Tamanho (nº de parâmetros)**      | Variável (cursor-small é menor e mais rápido; Claude/GPT são modelos massivos)                                                |
| **Acesso**                          | Planos de Assinatura (onde o custo dos modelos está incluso) ou através de API Keys Próprias                          |
| **Suporte a Fine-tuning**           | Não,                      |
| **Suporte a RAG**                   | Sim                                                      |
| **Métodos de prompting suportados** | CoT, ReAct, PoT (indireto), Self-Refine e Few-Shot (Automatizado com RAG)                            |
| **Ferramentas adicionais**          | LangChaine e LangGraph (RAG), Ollama e Groq (API), extensões VSCode (nativo)    |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Híbrido. A interface e indexação (RAG) ocorrem localmente; a inferência pesada (LLM) ocorre na Cloud. Existe um "Privacy Mode" que garante que o código não seja retido/treinado nos servidores, mas o processamento ainda é remoto. (Opção 100% local possível apenas via gambiarra/configuração manual de APIs como Ollama, não é o padrão)                 |
| **Infraestrutura utilizada no teste** |  Utiliza GPUs na nuvem para os modelos principais e processamento local (CPU/GPU do dev) para indexação e modelo preditivo leve.    |
| **Custos (quando aplicável)**         | Freemium (Plano Gratuito / Pro $20/mês / Business $40/usuário) ou custo por token do modelo usado se utilizado via API |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

Para cada item abaixo, descreva:

* **O que a ferramenta faz**
* **Como faz**
* **Exemplos / evidências**
* **Limitações observadas**

Use N/A quando não aplicável.

---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              |         Sim              |                Utiliza "Chat with Codebase" para extrair regras de negócio e requisitos implícitos já existentes no código ("Como o sistema calcula imposto atual?")          |
| Análise                 |         Sim             |                 O modo "Composer" permite analisar o impacto de novos requisitos em múltiplos arquivos simultaneamente.         |
| Priorização             |         Não             |                 Não possui um banco de dados de "User Stories" ou "Requisitos" onde se possa atribuir valores de negócio, urgência ou ROI para ordenar uma fila de trabalho.         |
| Modelagem               |         Sim              |                Interpretação de arquivos de texto ou diagramas (ex: Mermaid) para gerar código correspondente.  |
| Validação / Verificação |                     Sim  | Validação técnica de requisitos via "Shadow Workspace", onde a IA tenta implementar e verificar a viabilidade em background.                         |
| Documentação            |         Sim              |                Gera documentação automática baseada no código (docstrings, READMEs) e explicações de fluxos complexos. |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | Sim                      |        Ele atua na materialização da arquitetura (código e estrutura), mas não na modelagem visual abstrata.                  |
| Decisões arquiteturais           |         Sim             |                 Sugere refatorações estruturais e explica padrões utilizados no projeto.         |
| Avaliação de trade-offs          |             Sim          |                    Via chat, pode comparar abordagens de implementação sugeridas pela IA.      |
| Uso de padrões arquiteturais     |               Sim        |                      Reconhece e implementa padrões (MVC, Singleton, Factory) adaptados ao contexto do código existente    |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto |   Sim                    |           Sugere aplicação de Design Patterns durante a geração de código (ex: "Reescreva isso usando o padrão Strategy")               |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Sim                      |          Geração inline (Copilot++), completação de múltiplos arquivos (Composer) e edição via linguagem natural (Cmd+K).               |
| Refatoração       |                Sim       |                        Comandos diretos para refatorar funções, classes ou módulos inteiros para melhor legibilidade ou performance.|
| Detecção de bugs  |  Sim                     |    Analisa o código em tempo real para encontrar erros lógicos e sugere correções ("Auto-debug")                      |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) |  Sim                     |         Gera testes unitários e de integração automaticamente baseados no código selecionado.                 |
| Execução de testes automatizados                 |   Sim                    |           Pode executar testes em background (via Shadow Workspace) para validar correções geradas.               |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             |  Não                     |         Não atua como servidor de integração (runner), sendo incapaz de executar pipelines automáticos ou deploys após commits. Sua utilidade restringe-se estritamente à geração de scripts de configuração (IaC), deixando a execução e orquestração para plataformas dedicadas como GitHub Actions ou Jenkins.                 |
| Automação                         |Não                       |       A ferramenta não gerencia automação de processos de background ou infraestrutura em nuvem de forma autônoma (como cron jobs de servidores). A automação permitida pelo Cursor é local, limitando-se à geração e execução de scripts de terminal sob comando direto do desenvolvedor enquanto a IDE está aberta.                   |
| Monitoramento                     |  Não                     |         O Cursor não possui telemetria, dashboards ou alertas para verificar a saúde do software em tempo real. Ele não coleta métricas de execução em produção, servindo apenas para a depuração reativa de logs estáticos colados no chat.                 |
| Documentação técnica automatizada | Sim                      |         O Cursor utiliza o LLM para ler a base de código e gerar documentação técnica, docstrings e arquivos README de forma automática. Diferente de geradores estáticos, ele consegue inferir o contexto de negócio e explicar fluxos complexos em linguagem natural para facilitar a manutenção.                 |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas |                   Sim    |                          "Bug fixing" assistido pela IA, que lê a pilha de erros do terminal e sugere a correção (feature "Add to Chat" no terminal).|

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        |  Fraco                     |        Auxilia apenas no planejamento técnico imediato (decomposição de tarefas de código) através da funcionalidade "Plan Mode" ou chat. Ele não realiza o planejamento estratégico do projeto, não gerencia backlog de produto, nem cria estruturas analíticas de projeto (EAP/WBS).                  |
| Execução                            | Sim                      |         Atua como um co-piloto para a execução técnica da construção do software. Ele acelera a codificação e implementação das tarefas                 |
| Controle                            | Não                      |          Não possui mecanismos para monitorar o progresso do projeto em relação ao planejado ou gerenciar mudanças de escopo                 |
| Encerramento                        | Não                      |         O Cursor não oferece suporte a processos de encerramento formal, aceitação de entregáveis ou arquivamento administrativo do projeto.                 |
| Gestão de riscos                    |       Fraco                |             A análise de risco limita-se à identificação de vulnerabilidades de segurança e bugs lógicos dentro do código-fonte              |
| Estimativas (tempo, custo, esforço) |  Não                      |        O Cursor AI não possui calendário, cronograma ou noções de tempo de entrega (deadlines). Ele não gerencia o caminho crítico nem alerta sobre atrasos. A ferramenta é totalmente desconectada da gestão financeira, não permitindo orçamentação e controle de custos de desenvolvimento.  O Cursor não é capaz de realizar estimativas de esforço (como Story Points ou horas) para um conjunto de requisitos.                 |
| Medição                             | Não                      |         Não há coleta de métricas de processo (como Lead Time, Cycle Time ou densidade de defeitos) para análise gerencial. O Cursor não gera relatórios de produtividade ou qualidade do processo de engenharia, servindo apenas como editor e não como ferramenta de BI.                 |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐            | Altíssima na Construção e Testes Unitários. Elevada pelo uso de Shadow Workspace, que tenta implementar e validar a viabilidade em background antes de sugerir.            |
| Profundidade técnica                | ⭐⭐⭐⭐            | Excelente em padrões de código (MVC, Singleton) , mas falha em modelagem visual abstrata e arquitetura de enxame (swarm).            |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            | Ele conecta requisitos (comentários) à construção (código) e aos testes, entendendo o impacto de uma mudança na arquitetura do projeto todo            |
| Clareza                             | ⭐⭐⭐⭐⭐            |  Gera explicações de fluxos complexos em linguagem natural para documentação e interpreta arquivos de texto/diagramas.           |
| Aderência às melhores práticas      | ⭐⭐           |  Sugere ativamente a refatoração para Design Patterns (ex: Strategy) e melhoria de legibilidade. Entretanto é extremente ineficiente em DevOps e gerenciamento.          |
| Consistência entre respostas        | ⭐⭐⭐⭐            | Possui loops nativos de Self-Refine e análise de erros para refinar a lógica.            |
| Ocorrência de alucinações           | Baixa |   O mecanismo Program-of-Thought (PoT) reduz alucinações ao rodar linters em background para verificar a validade da solução          |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

Criar um módulo de API para gerenciamento de Usuários (CRUD) usando Python (FastAPI) e SQLAlchemy, incluindo validação de e-mail e testes unitários.

### ● Resultados quantitativos
#### Usando IA
* Tempo: 8 minutos.
* Número de erros: 1 (Alucinação em import de lib não instalada).
* Qualidade do código: Alta (Consistente com PEP8 e Padrões de Projeto ).
* Cobertura de testes: Alta (>90%). 
* Documentação: Completa (Docstrings geradas)

#### Sem uso de IA
* Tempo: 45 minutos.
* Número de erros: 3 a 5 (Typos, imports esquecidos).
* Qualidade do código: Variável (depende do cansaço do dev).
* Cobertura de testes: Baixa (Geralmente "Caminho Feliz"). 
* Documentação: Geralmente ignorada no rascunho.

### Comentários qualitativos
**Contexto e Coerência**: Ao solicitar a criação do CRUD, o Cursor utilizou o recurso de RAG (Embeddings) para entender a estrutura de pastas existente. Diferente de um LLM comum que daria um script único, o modo Composer separou corretamente os arquivos em models.py, schemas.py e routes.py

**Autocorreção (Auto-debug)**: Durante a implementação, houve um erro de importação circular. A funcionalidade de Auto-debug analisou a pilha de erros no terminal e sugeriu a correção automaticamente, lendo o contexto do erro e refinando a lógica.


**Refinamento de Requisitos**: O Cursor conseguiu extrair requisitos implícitos. Ao ver que o projeto usava JWT em outros módulos (via Chat with Codebase), ele sugeriu adicionar a proteção de rota no novo CRUD sem que fosse explicitamente pedido.

**Limitação Percebida**: A ferramenta não conseguiu instalar as dependências automaticamente ou rodar o servidor sozinha em background para teste final (deployment), limitando-se a gerar os scripts, pois não possui automação autônoma de processos de infraestrutura.
### ● Exemplos (copie trechos de código, respostas etc.)
```python
# schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    name: str = Field(..., min_length=3)
    email: EmailStr  # IA escolheu corretamente o tipo EmailStr
    password: str = Field(..., min_length=8)
    role: str = "user"

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    
    class Config:
        from_attributes = True # Atualizado para Pydantic v2 automaticamente
```
```python
# tests/test_users.py
def test_create_user_duplicate_email(client, db_session):
    # Cenário gerado pela IA para validar unicidade
    create_user(db_session, email="test@example.com")
    
    response = client.post("/users/", json={
        "name": "Test Duplicate",
        "email": "test@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"
```
---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* **Redução da Carga Cognitiva na Manutenção**: O Cursor atua fortemente na gestão do conhecimento de projetos legados. Ele gera documentação automática (docstrings, READMEs) e explica fluxos complexos em linguagem natural. Isso acelera o onboarding de novos desenvolvedores e a compreensão de regras de negócio implícitas no código.



* **Antecipação da Validação (Shift-Left Testing)**: A ferramenta promove a qualidade contínua ao validar a viabilidade técnica em background (via "Shadow Workspace"). Ela não apenas gera testes, mas pode executá-los para validar correções instantaneamente, movendo a etapa de verificação para o momento da construção.


* **Consistência Arquitetural Automatizada**: Atua como um "revisor de código" que conhece o contexto, sugerindo refatorações estruturais e explicando padrões utilizados. Ele reconhece e implementa padrões de projeto (como MVC, Singleton, Factory) adaptados ao estilo do código existente, garantindo aderência às normas técnicas sem intervenção humana constante.


* **Análise de Impacto de Mudanças**: No ciclo de engenharia de requisitos, a ferramenta mitiga o risco de efeitos colaterais. O modo "Composer" permite analisar o impacto de novos requisitos em múltiplos arquivos simultaneamente, garantindo que uma alteração em uma regra de negócio se propague corretamente por todo o sistema.

### **Limitações**

* **Desconexão com o Valor de Negócio (Priorização**): A ferramenta é incapaz de auxiliar na engenharia de valor. Não existe um banco de dados de "User Stories" para priorização baseada em ROI ou urgência. Ela executa tarefas técnicas, mas não sabe "o que é mais importante" para o negócio.

* **Ausência de Métricas de Processo (Gestão)**: Para um gerente de engenharia, o Cursor é uma "caixa preta". Ele não coleta métricas fundamentais como Lead Time, Cycle Time ou densidade de defeitos. Não gera relatórios de produtividade ou qualidade do processo, servindo apenas como editor e não como ferramenta de BI.


* **Inexistência de Gestão de Projetos (Prazos e Custos)**: A ferramenta ignora restrições de projeto. Não possui cronograma, gestão de caminho crítico ou noções de deadlines. Também é totalmente desconectada da gestão financeira, não permitindo orçamentação ou controle de custos de desenvolvimento. Além disso, é incapaz de realizar estimativas de esforço (como Story Points).



* **Limitação Operacional (DevOps e Telemetria)**: O Cursor não fecha o ciclo DevOps. Ele não atua como servidor de CI/CD nem executa pipelines de deploy. Em produção, ele é cego: não possui telemetria, dashboards ou alertas para monitorar a saúde do software em tempo real.

* **Abstração Visual Limitada**: Embora materialize a arquitetura em código, ele falha na modelagem visual abstrata. Não substitui ferramentas de desenho de arquitetura necessárias para comunicar a visão do sistema para stakeholders não técnicos.

* **Colaboração Limitada (Single-Agent)**: Atualmente, opera sob o paradigma de um único "Assistente" e não possui uma arquitetura de enxame (swarm) onde múltiplos agentes especializados colaboram.

---

#  **8. Riscos, Custos e Considerações de Uso**

## Riscos
* **Risco de Gestão de Projetos (Cegueira Temporal)**: O Cursor não gerencia o caminho crítico nem alerta sobre atrasos. Ele não possui calendário, cronograma ou noções de tempo de entrega (deadlines). O risco aqui é o time focar na execução técnica acelerada enquanto perde a visão dos prazos gerais.



* **Limitação na Análise de Risco**: A análise de risco da ferramenta é estritamente técnica, limitando-se à identificação de vulnerabilidades de segurança e bugs lógicos dentro do código-fonte. Ela não avalia riscos de negócio ou de viabilidade de escopo.


* **Privacidade e Processamento Remoto**: Embora exista um "Privacy Mode" que garante que o código não seja retido ou treinado nos servidores, o processamento da inferência pesada (LLM) ocorre na Cloud, em um modelo híbrido. O uso 100% local é possível apenas via configurações manuais não-padrão (gambiarra).



* **Ausência de Processos de Encerramento**: A ferramenta não oferece suporte a processos de encerramento formal, aceitação de entregáveis ou arquivamento administrativo do projeto.

## Custos
* Modelos de Licenciamento (SaaS):
    * Freemium: Plano Gratuito disponível.


    * Pro: Custo de $20 por mês.


    * Business: Custo de $40 por usuário.


* Infraestrutura Híbrida: O Cursor utiliza GPUs na nuvem para os modelos principais (inferência pesada). No entanto, ele consome recursos locais (CPU/GPU do desenvolvedor) para indexação e modelos preditivos leves.



* Descontrole Financeiro do Projeto: A ferramenta é totalmente desconectada da gestão financeira. Ela não permite orçamentação, controle de custos de desenvolvimento ou estimativas de esforço financeiro.

## Considerações de Uso
O cursor é um editor de código superdotado, não um gerente de projetos ou operador de infraestrutura, criando-se, assim, um descompasso entre a ferramenta e os propositos do projeto AI4SE.


* Escopo de Automação (Local vs. Servidor): A automação permitida pelo Cursor é local, limitando-se à geração e execução de scripts de terminal enquanto a IDE está aberta. Ele não gerencia processos de background autônomos ou cron jobs em servidores.



* Papel no DevOps (Geração vs. Execução): O Cursor não atua como servidor de integração (runner) e é incapaz de executar pipelines automáticos ou deploys. Sua utilidade restringe-se à geração de scripts de configuração (IaC), deixando a orquestração para ferramentas como GitHub Actions ou Jenkins.


* Monitoramento e Métricas: Não utilize o Cursor esperando dados de BI. Ele não possui telemetria, dashboards ou alertas de saúde do software em tempo real. Também não coleta métricas de processo como Lead Time ou densidade de defeitos.



* Planejamento Técnico vs. Estratégico: A ferramenta auxilia apenas no planejamento técnico imediato (decomposição de tarefas de código). Ela não realiza planejamento estratégico, gestão de backlog ou criação de estruturas analíticas de projeto (EAP).



* Modelos de IA Envolvidos: O uso considera modelos de fronteira como Claude 3.5 Sonnet (padrão atual) e GPT-4o , além de um modelo menor customizado (cursor-small) para completação rápida.
---

#  **9. Conclusão Geral da Análise**


O Cursor AI posiciona-se como uma ferramenta de execução técnica e tática da Engenharia de Software. Sua adequação é máxima nas fases de:


* Construção e Codificação: Atua como um "Copilot++" para geração inline, completação de múltiplos arquivos e refatoração via linguagem natural.


* Manutenção e Evolução: Ideal para compreender bases de código legado, gerando documentação automática e explicando fluxos complexos, além de realizar correção de bugs assistida.



* Verificação e Validação (Nível Unitário): Adequada para a implementação de Shift-Left Testing, gerando e validando testes unitários e de integração localmente antes do commit.


* Detalhamento Técnico de Requisitos: Útil para transformar especificações textuais em esqueletos de código e analisar o impacto de mudanças em múltiplos arquivos.


A ferramenta deve ser evitada em atividades que exigem visão estratégica, temporal ou operacional autônoma:


* Gerenciamento de Projetos: Não deve ser usada para estimar prazos, custos, controlar cronogramas ou gerenciar o caminho crítico do projeto, pois é "cega" temporal e financeiramente.


* Orquestração de DevOps: Não substitui ferramentas de CI/CD (como Jenkins ou GitHub Actions), pois não executa pipelines automáticos nem realiza deploys em ambientes de produção.


* Monitoramento de Produção: Inadequada para Observabilidade (SRE), pois não coleta métricas de execução, logs de saúde ou telemetria em tempo real.


* Priorização de Negócio: Não serve para definir "o que fazer primeiro" (backlog), pois não compreende ROI ou urgência de negócio.

O Cursor encontra-se em um estágio de Maturidade de "Fronteira" (State-of-the-Art) no nicho de Coding Assistants.

* Diferencia-se de simples chatbots por integrar tecnologias avançadas como Shadow Workspace (que valida a viabilidade do código em background) e RAG Local (indexação vetorial de todo o repositório).



* Utiliza modelos de ponta (Claude 3.5 Sonnet, GPT-4o) combinados com modelos proprietários menores (cursor-small) e fine-tuning específico para prever a "próxima edição" e não apenas a "próxima palavra".


* Implementa conceitos complexos de agentes como ReAct (no terminal) e Program-of-Thought de forma transparente ao usuário.

Vale a pena para a organização?
Sim, mas como ferramenta de produtividade individual, não de gestão.


* Ganhos: Vale a pena pela drástica redução na carga cognitiva de manutenção e pela aceleração da etapa de codificação e testes. Ela transforma o desenvolvedor de um "escritor de código" em um "arquiteto e revisor", elevando a qualidade técnica através da sugestão ativa de padrões de projeto e correções.




* Ressalva: A organização não deve esperar que a ferramenta reduza a necessidade de gerentes de projeto ou engenheiros de DevOps, pois o Cursor não cobre essas lacunas do ciclo de vida. O investimento ($20-$40/usuário) retorna em velocidade de entrega técnica, desde que o gerenciamento humano permaneça no comando das decisões estratégicas.

---

#  **10. Referências e Links Consultados**

* [Site oficial](https://cursor.com/)
* [Blog oficial](https://cursor.com/blog)
* [Documentação](https://docs.cursor.com/)
* [Composer (Agente AI Nativo)](https://cursor.com/blog/2-0)
* [Codebase Indexing](https://cursor.com/docs/context/codebase-indexing)
* [Cursor Pricing](https://cursor.com/docs/account/pricing)
* [Privacidade e Governança](https://cursor.com/docs/enterprise/privacy-and-data-governance)
* [Integração com Claude 3.5](https://medium.com/towards-agi/how-to-use-cursor-ai-with-claude-3-5-sonnet-step-by-step-guide-4e1bbdd7bd65)
* [Shadow Workspace](https://cursor.com/blog/shadow-workspace)