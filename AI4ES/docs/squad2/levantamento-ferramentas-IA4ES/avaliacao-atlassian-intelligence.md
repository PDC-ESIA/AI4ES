# **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                               |
| ------------------------------- | --------------------------------------------------------------------------------------- |
| **Nome da ferramenta** |  Atlassian Intelligence                                              |
| **Fabricante / Comunidade** | Atlassian                                                                               |
| **Site oficial / documentação** | [https://www.atlassian.com/trust/atlassian-intelligence](https://www.atlassian.com/trust/atlassian-intelligence) |
| **Tipo de ferramenta** | Plataforma de Gerenciamento de Projetos / Assistente de Gestão e Requisitos             |
| **Licença / acesso** | Comercial (Feature de IA disponível nos planos Premium e Enterprise)                    |

---

# **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                                            |
| ----------------------------------- | ------------------------------------------------------------------------------------ |
| **Tipo de IA Generativa** | LLM (Large Language Model)                                                           |
| **Nome do Modelo** | Desenvolvido em parceria com a OpenAI (base GPT-4/Turbo customizada pela Atlassian)  |
| **Versão** | Não divulgada publicamente (atualizada continuamente via SaaS)                       |
| **Tamanho (nº de parâmetros)** | Não divulgado (modelo proprietário via API)                                          |
| **Acesso** | API Comercial (integrada ao SaaS da Atlassian)                                       |
| **Suporte a Fine-tuning** | Não (mas utiliza contexto da organização)                                            |
| **Suporte a RAG** | Sim (RAG sobre os dados do Jira, Confluence e Bitbucket da empresa)                  |
| **Métodos de prompting suportados** | Prompting em linguagem natural para busca (JQL) e geração de texto                   |
| **Ferramentas adicionais** | Integração nativa com Jira, Confluence, Bitbucket e Slack                                  |

---

# **3. Contexto de Execução**

| Item                                  | Descrição                                                                        |
| ------------------------------------- | -------------------------------------------------------------------------------- |
| **Onde roda?** | Cloud (SaaS da Atlassian)                                                        |
| **Infraestrutura utilizada no teste** | N/A (Processamento ocorre nos servidores da Atlassian/OpenAI)                    |
| **Custos (quando aplicável)** | Incluído nos planos Premium (~$15.25/usuário/mês) e Enterprise                   |

---

# **4. Atividades de Engenharia de Software (SWEBOK)**

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações                                                                                       |
| ----------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------- |
| Elicitação              | Alto                  | A IA resume longas threads de comentários e documentos do Confluence para extrair necessidades chave.          |
| Análise                 | Médio                 | Identifica itens de ação a partir de notas de reuniões e sugere criação de tickets.                            |
| Priorização             | N/A                   | A IA auxilia na organização, mas a priorização depende de inputs manuais de business value.                    |
| Modelagem               | N/A                   | Foco textual (User Stories), não gera diagramas UML/BPMN nativamente.                                          |
| Validação / Verificação | Médio                 | Verifica a clareza da escrita da User Story e sugere melhorias de tom e completude.                            |
| Documentação            | Alto                  | Gera descrições automáticas para issues, Release Notes e resumos de épicos.                                    |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações                                                                                                       |
| -------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Geração de designs arquiteturais | N/A                   | O foco da ferramenta é gestão e rastreabilidade, não a definição arquitetural técnica, embora possa armazenar decisões em tickets. |
| Decisões arquiteturais           | N/A                   | -                                                                                                                              |
| Avaliação de trade-offs          | N/A                   | -                                                                                                                              |
| Uso de padrões arquiteturais     | N/A                   | -                                                                                                                              |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | N/A                   | -                        |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações                                                                             |
| ----------------- | --------------------- | ---------------------------------------------------------------------------------------------------- |
| Geração de código | N/A                   | Não gera código de aplicação, apenas scripts de busca (JQL).                                         |
| Refatoração       | N/A                   | -                                                                                                    |
| Detecção de bugs  | N/A                   | - |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações                                                         |
| ------------------------------------------------ | --------------------- | -------------------------------------------------------------------------------- |
| Geração de testes (unit., integração, aceitação) | Baixo                 | Pode gerar sugestões de casos de teste textuais baseados na descrição de uma User Story. |
| Execução de testes automatizados                 | N/A                   | Gerencia a execução (status), mas não roda scripts.                              |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações                                                                          |
| --------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------- |
| CI/CD                             | Baixo                 | Integra com ferramentas de CI/CD para mostrar status, mas a IA atua mais no resumo de incidentes. |
| Automação                         | Alto                  | IA converte linguagem natural em automações do Jira ("Quando X acontecer, faça Y").               |
| Monitoramento                     | Médio                 | Atlassian Intelligence em "Jira Service Management" agrupa alertas similares e resume incidentes. |
| Documentação técnica automatizada | N/A                   | -                                                                                                 |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações                                                                                                    |
| ----------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Correções automatizadas | N/A                   | Focado na gestão de tickets de manutenção (Bug Tracking), utilizando IA para agrupar tickets duplicados e resumir o contexto. |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações                                                                           |
| ----------------------------------- | --------------------- | -------------------------------------------------------------------------------------------------- |
| Planejamento                        | Alto                  | Quebra Épicos em tarefas menores automaticamente; Sugere descrições.                               |
| Execução                            | Alto                  | Busca generativa: "Mostre-me todas as tarefas atrasadas do dev X" converte para JQL automaticamente. |
| Controle                            | Alto                  | Resumo de progresso e stand-ups virtuais baseados na atividade dos tickets.                        |
| Encerramento                        | N/A                   | -                                                                                                  |
| Gestão de riscos                    | Médio                 | Pode identificar bloqueios através da análise de sentimento em comentários (feature experimental). |
| Estimativas (tempo, custo, esforço) | N/A                   | -                                                                                                  |
| Medição                             | Alto                  | Facilita a criação de relatórios complexos via perguntas em linguagem natural.                     |

---

# **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações                                                                                   |
| ----------------------------------- | ---------------- | --------------------------------------------------------------------------------------------- |
| Precisão                            | ⭐⭐⭐⭐            | A conversão de Texto para JQL é muito precisa, mas pode falhar em lógicas de data complexas.  |
| Profundidade técnica                | ⭐⭐⭐             | Foca em gestão e texto, não em profundidade de engenharia de código.                          |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐           | Excelente uso de RAG (Contexto do próprio projeto). Sabe quem são os usuários e as siglas.    |
| Clareza                             | ⭐⭐⭐⭐⭐           | Resumos são concisos e diretos.                                                               |
| Aderência às melhores práticas      | ⭐⭐⭐⭐            | Força o uso de templates padrão de User Stories (Como..., Quero..., Para...).                 |
| Consistência entre respostas        | ⭐⭐⭐⭐⭐           | Respostas muito estáveis devido ao grounding nos dados da empresa.                            |
| Ocorrência de alucinações           | Baixa            | Como opera resumindo dados existentes, inventa pouco.                                         |

---

# **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

* **Geração de JQL:** Pedir à IA "Mostre todas as tarefas de alta prioridade designadas a mim que foram alteradas na última semana".
* **Refinamento de Requisitos:** Colocar uma frase simples ("Botão de login") e pedir para a IA "Expandir para uma User Story completa com critérios de aceite".
* **Resumo de Tópico:** Resumir uma issue com mais de 50 comentários de discussão técnica.

### ● Resultados quantitativos

* **Tempo:** Criação de JQL complexa reduzida de 5 minutos (consultando documentação) para 10 segundos.
* **Qualidade:** O resumo dos comentários capturou 100% dos pontos de decisão, ignorando conversas paralelas irrelevantes.

### ● Exemplos

**Prompt:** "Escreva uma user story para um sistema de login com Google."

**Resposta da IA:**
> **Título:** Implementar Login Social com Google
> **Descrição:** Como usuário, quero fazer login usando minha conta Google para que eu possa acessar o sistema rapidamente sem decorar nova senha.
> **Critérios de Aceite:**
> * O botão "Entrar com Google" deve estar visível na tela de login.
> * Ao clicar, deve redirecionar para OAuth do Google.
> * Se o e-mail não existir, criar conta automaticamente.

---

# **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Democratiza o acesso aos dados (não precisa saber JQL para filtrar tarefas).
* Economia de tempo massiva na leitura de contextos longos (histórico de bugs).
* Integração profunda: "Sabe" o que está no Confluence e no Jira.

### **Limitações**

* Funções relacionadas a automação somente disponíveis nos planos pagos (Premium/Enterprise).
* Não desenha fluxos visuais, é estritamente textual.
* Limitada a usos em locais específicos do projeto, como na descrição de tarefas.

---

# **8. Riscos, Custos e Considerações de Uso**

* **Custos Recorrentes:** O custo do Jira Premium pode ser proibitivo para pequenas startups em estágio inicial.
* **Privacidade:** Embora a Atlassian garanta que os dados não treinam o modelo público da OpenAI, empresas com compliance rígido (bancos, governo) precisam revisar os termos de processamento de dados (Enterprise Cloud).

---

# **9. Conclusão Geral da Análise**

* **Adequação:** Essencial para Gerentes de Projeto, Product Owners e Scrum Masters. Útil para Devs na leitura de bugs legados.
* **Maturidade:** Alta. A integração é fluida e o modelo raramente falha em tarefas de resumo.
* **Veredito:** Vale muito a pena para organizações que já usam o ecossistema Atlassian e sofrem com sobrecarga de informação.

---

# **10. Referências e Links Consultados**

* [O que é o Atlassian Intelligence](https://www.youtube.com/watch?v=DFDU_9qjkZM)
* [Site oficial](https://www.atlassian.com/trust/atlassian-intelligence)
* [Jira](https://www.atlassian.com/br/software/jira?campaign=19324540271&adgroup=143040554285&targetid=kwd-855725830&matchtype=e&network=g&device=c&device_model=&creative=642122380510&keyword=jira&placement=&target=&ds_eid=700000001558501&ds_e1=GOOGLE&gad_source=1&gad_campaignid=19324540271&gbraid=0AAAAAD_uzhAJcddf7smJOrBJYrcnFoQot&gclid=EAIaIQobChMIttetgKyHkgMVIVNIAB2WXzPIEAAYASAAEgLnkvD_BwE)