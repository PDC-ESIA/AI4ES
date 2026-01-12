# 1. Identificação da Ferramenta

| Item | Descrição |
|---|---|
| Nome da ferramenta | Amazon Q Developer |
| Fabricante / Comunidade | Amazon Web Services (AWS) |
| Site oficial / documentação | https://aws.amazon.com/q/developer/ |
| Tipo de ferramenta | Assistente de código baseado em IA (Plugin de IDE e Agente de Software) |
| Licença / acesso | Híbrido (Nível gratuito "Free Tier" e versão Profissional paga) |

# 2. Informações do Modelo de IA Utilizado

| Item | Descrição |
|---|---|
| Tipo de IA Generativa | LLM (Large Language Model) |
| Nome do Modelo | Família Claude 3 (Anthropic) otimizada pela AWS |
| Versão | Claude 3.5 Sonnet / Claude 3 Haiku (dependendo da tarefa) |
| Tamanho (nº de parâmetros) | Não divulgado publicamente pela AWS |
| Acesso | API comercial via AWS Bedrock (interno) / Extensões de IDE |
| Suporte a Fine-tuning | Sim (via personalização com dados do cliente na versão Pro) |
| Suporte a RAG | Sim (Contexto local do repositório e bases de conhecimento) |
| Métodos de prompting suportados | CoT, ReAct, Chat direto e Comandos de Slash (/fix, /test) |
| Ferramentas adicionais | Extensões VSCode/JetBrains, AWS CLI, Console AWS |

# 3. Contexto de Execução

| Item | Descrição |
|---|---|
| Onde roda? | Cloud (Processamento na AWS) |
| Infraestrutura utilizada no teste | Serviço gerenciado via AWS Bedrock |
| Custos (quando aplicável) | Gratuito (Free) ou US$ 19/mês (Pro) |

# 4. Atividades de Engenharia de Software (SWEBOK)

Para cada item abaixo, descreva:

-  **O que a ferramenta faz**
-  **Como faz**
-  **Exemplos / evidências**
-  **Limitações observadas**

Use N/A quando não aplicável.

## 4.1. Requisitos de Software

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
|---|---|---|
| Elicitação | Parcial | Atua como um parceiro de brainstorming. Ao fornecer um tema (ex: "Sistema de gestão de estoque farmacêutico"), ele pode gerar uma lista de requisitos funcionais e não funcionais, assim como atas para guiar uma possível reunião com o cliente. |
| Análise | Alto | Capaz de gerar requisitos a partir de uma história de usuário ou descrição de atividade, capaz identificar inconsistências entre os requisitos e regras de negócio descritas no chat ou em arquivos do projeto através do suporte a RAG. |
| Priorização | Médio | Capaz de analisar quais funcionalidades devem ser priorizadas e quais podem ser postergadas durante a produção de um software, mas requer intervenção humana pesada; a IA pode sugerir prioridade com base em esforço técnico, mas não possui visão de valor de negócio real. |
| Modelagem | Médio | Consegue auxiliar na criação de diagramas. Ao fornecer o tema (ex: "Sistema de gestão de estoque farmacêutico") e solicitar a criação de um diagrama de classes UML com base no requisitos e informações já existentes nos arquivos do projeto, a IA consegue gerar, mas sem respeitar todos os princípios da engenharia de software e do paradigma OO. |
| Validação / Verificação | Alto | Pode verificar se um código implementado atende aos requisitos descritos nos comentários, no chat principal ou na documentação do repositório via RAG, além de poder gerar casos de teste, executar o código e verificar se o resultado está saindo como deveria. |
| Documentação | Alto | Gera User Stories, Critérios de Aceite e arquivos de especificação técnica (Markdown) a partir de prompts simples ou comandos de chat. |

## 4.2. Arquitetura de Software

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
|---|---|---|
| Geração de designs arquiteturais | Alto | Capaz de sugerir arquiteturas completas (ex:Padrão Principal: Layered Architecture e Domain-Driven Design) com base nas necessidades do projeto, avaliado com o auxílio do RAG. |
| Decisões arquiteturais | Médio | Auxilia na escolha de componentes (ex: quando usar DynamoDB vs Aurora). |
| Avaliação de trade-offs | Médio | Consegue listar prós e contras de diferentes abordagens (Custo vs. Performance), utilizando o conhecimento da família Claude 3.5. |
| Uso de padrões arquiteturais | Alto | Implementa padrões como Event-Driven, Hexagonal ou Layered Architecture ao gerar estruturas de pastas e esqueletos de projetos. |

## 4.3. Design de Software

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
|---|---|---|
| Sugestão/uso de padrões de projeto | Alto | Identifica onde aplicar padrões (Factory, Strategy, Observer) no código existente e sugere refatorações para aplicar SOLID ou Clean Code. |

## 4.4. Construção de Software

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
|---|---|---|
| Geração de código | Muito Alto | Funcionalidade central via extensões para VS Code e JetBrains, oferecendo sugestões de código em tempo real e autocompletar baseado no contexto. |
| Refatoração | Alto | Ao apresentar um código e explicitar a finalidade, é possível solicitar a refatoração (ajustar/otimizar/simplificar) do código, e isso pode ser feito de várias maneiras, sendo algumas dessas: por meio do chat, solicitando a refatoração do código, comandos específicos (/review, /dev) e função disponibilizada na própria interface, por cliques. |
| Detecção de bugs | Alto | É possível solicitar o review (/review) do código, o que analisa e procura possíveis bugs, algo incluso na refatoração. |

## 4.5. Teste de Software

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
|---|---|---|
| Geração de testes (unit., integração, aceitação) | Muito Alto | Suporte nativo via comando /test, que analisa o código-fonte e gera suítes de testes unitários automaticamente. |
| Execução de testes automatizados | Médio | Embora não execute os testes diretamente no seu hardware, a ferramenta pode gerar scripts de execução e ajudar a interpretar falhas de logs através do chat. |

## 4.6. Operações de Software

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
|---|---|---|
| CI/CD | Alto | Auxilia na criação de arquivos de configuração para pipelines de CI/CD e integração com serviços como AWS CodePipeline e GitHub Actions. |
| Automação | Alto | Suporte via AWS CLI e Console AWS, permitindo a geração de scripts de automação de infraestrutura e gerenciamento de recursos via chat. |
| Monitoramento | Médio | Capaz de explicar métricas do CloudWatch e sugerir consultas (queries) para logs, facilitando o diagnóstico de incidentes operacionais no ambiente AWS. |
| Documentação técnica automatizada | Alto | Gera documentação de infraestrutura (IaC) e explicações detalhadas sobre recursos provisionados na nuvem a partir de prompts técnicos. |

## 4.7. Manutenção de Software

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
|---|---|---|
| Correções automatizadas | Alto | Através do comando /fix ou do agente de software, a ferramenta analisa erros de compilação ou vulnerabilidades de segurança e propõe patches diretamente no código. |

## 4.8. Gerenciamento de Projeto de Software

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
|---|---|---|
| Planejamento | Médio | Ajuda a quebrar grandes épicos em tarefas menores e sugerir sequenciamento técnico, baseando-se na lógica de raciocínio do modelo Claude 3.5. |
| Execução | Alto | O Amazon Q Developer atua como um "Agente de Software", sendo capaz de implementar funcionalidades inteiras a partir de descrições em linguagem natural. |
| Controle | Baixo | Não possui integração nativa para monitorar cronogramas (Gantt) ou quadros Kanban, limitando-se ao controle de qualidade do código. |
| Encerramento | Médio | Auxilia na criação de relatórios de entrega, resumos de pull requests e documentação de "lições aprendidas" técnicas com base nos logs do chat. |
| Gestão de riscos | Médio | Identifica riscos técnicos (débito técnico, bibliotecas obsoletas ou falhas de segurança) que podem comprometer o cronograma ou a estabilidade. |
| Estimativas (tempo, custo, esforço) | Baixo | Pode estimar a complexidade de uma função, mas não possui contexto organizacional para prever prazos reais ou custos de pessoal. |
| Medição | Médio | Capaz de analisar o código para extrair métricas de complexidade e sugerir melhorias de performance que impactam o custo de infraestrutura na AWS. |

# 5. Qualidade das Respostas

| Critério | Avaliação | Observações |
|---|---|---|
| Precisão |⭐⭐⭐⭐| Corrigiu incoerências críticas em requisitos (regra FIFO) e identificou erros lógicos em código (inicialização de variáveis). Teve um deslize ao alterar arquivos sem comando direto, mas corrigiu prontamente. |
| Profundidade técnica |⭐⭐⭐⭐⭐| Demonstrou domínio ao sugerir padrões como Chain of Responsibility para validações complexas e ao realizar análise profunda de bugs via comando /review. |
| Contextualização no código/problema |⭐⭐⭐⭐⭐| Mapeou corretamente o domínio farmacêutico (ANVISA) e demonstrou consciência do workspace ao detectar arquivos deletados e sugerir novos caminhos de import. |
| Clareza |⭐⭐⭐⭐⭐| Respostas bem estruturadas com listas e exemplos práticos. Explicou de forma didática o uso de slash commands e referências com @. |
| Aderência às melhores práticas |⭐⭐⭐⭐⭐| Recomendou padrões de mercado como Clean Architecture, SOLID.. |
| Consistência entre respostas |⭐⭐⭐⭐⭐| As definições de arquitetura e padrões de projeto mantiveram-se alinhadas com as User Stories e códigos gerados posteriormente. |
| Ocorrência de alucinações | Baixa | A ferramenta mostrou-se capaz de identificar erros reais nos inputs do usuário (incoerências em documentos e bugs em código) em vez de apenas concordar com o erro. |

# 6. Experimentos Realizados

-  Descrição das tarefas testadas
-  Elicitação e Análise de Requisitos: Criação de ata de reunião com 28 perguntas de conformidade e definição de requisitos funcionais/não-funcionais para um sistema de farmácia.
-  Modelagem de Sistemas: Geração de diagramas de classes em formatos Mermaid e PlantUML.
-  Arquitetura e Design: Definição de estrutura de pastas seguindo Clean Architecture e sugestão de padrões de projeto (Strategy, Observer, Factory).
-  Codificação e Refatoração: Implementação de lógica de Fibonacci, ajuste de imports entre diretórios e refatoração de código, buscando o aumento de eficiência e correções.
-  Revisão de Código (Code Review): Uso do comando / review para identificar bugs críticos de lógica e inicialização de variáveis.
-  Geração de Testes: Uso do comando / test para criar suítes de testes unitários com unittest cobrindo casos de borda.

## • Resultados quantitativos

| Métrica | Resultado Estimado / Observado |
|---|---|
| Tempo com IA x sem IA | Redução estimada de ~70% no tempo de bootstrapping (criação de documentos e estrutura inicial de pastas). |
| Número de erros | A IA identificou 1 erro de lógica nos requisitos (FIFO) e 1 erro crítico no código (inicialização a,b=0,0). |
| Qualidade do código | Alta. O código gerado seguiu padrões PEP8 e incluiu tratamento de entradas inválidas nos testes. |
| Cobertura de testes | Cobertura total da função principal, incluindo casos base (n=1, n=2) e valores maiores (n=10). |
| Comentários qualitativos | A ferramenta demonstrou alta consciência de contexto (RAG) ao perceber arquivos deletados e ajustar imports automaticamente. |

## • Exemplos (Destaques de Desempenho)

**Exemplo 1: Elicitação e Refinamento de Requisitos (Alta Performance) A IA** não apenas listou funcionalidades, mas transformou uma ideia vaga em um backlog técnico estruturado e mensurável.

-  **Input do Usuário: "O sistema deve ser rápido e aceitar muitos usuários."**
-  **Resposta da IA: Converteu o requisito subjetivo em métricas de engenharia** de software: "Tempo de resposta para consulta: < 1s; Processamento de venda: < 3s; Suporte a pico de acesso de 200 usuários em 15 minutos".
-  **Impacto: Redução drástica na ambiguidade do projeto logo na fase inicial.**

**Exemplo 2: Análise Crítica e Detecção de Inconsistências A IA demonstrou** "autocrítica" ao analisar documentos fornecidos pelo usuário, encontrando erros que passariam despercebidos.

-  **Cenário: Durante a revisão do arquivo requisitos-sistema.md, a IA** identificou uma contradição lógica no controle de lotes.
-  **Evidência: "Identifiquei uma incoerência crítica no RF03. Há duas linhas** contraditórias: Linha 20: 'Controlar FIFO' e Linha 21: 'Não controlar FIFO'. Vou corrigir removendo a linha contraditória".**

**Exemplo 3: Suporte à Decisão Arquitetural e Design Patterns Diferente de um** simples gerador de código, a IA atuou como consultora de design, sugerindo padrões baseados na regra de negócio.

-  **Sugestão Técnica: Para o problema de validar diferentes tipos de receitas** (A, B e C), a IA sugeriu o uso do padrão Strategy.
-  **Justificativa da IA: "Permite isolar as regras distintas de cada tipo de** medicamento, facilitando a manutenção e a conformidade com a ANVISA".**

**Exemplo 4: Debugging Avançado com /review O uso de comandos** especializados permitiu identificar falhas de lógica em implementações já existentes.

-  **Comando:** /review @fibonnaci.py
-  **Resultado: "Critical Issue Found: The initialization a, b = 0, 0 is incorrect and** will cause wrong results for all n > 2. The correct initialization should be a, b = 0, 1".**
-  **Impacto: Prevenção de bugs em produção através de análise estática** inteligente.

# 7. Pontos Fortes e Fracos da Ferramenta

### Pontos fortes

-  **Capacidade Analítica Superior: A ferramenta não é apenas um** autocompletar; ela é capaz de identificar contradições lógicas em documentos de requisitos (como o conflito no controle FIFO) e bugs críticos em algoritmos (como o erro de inicialização na sequência de Fibonacci).
-  **Consciência de Contexto (Workspace Awareness): Demonstra alta** eficiência ao navegar pelo repositório, sugerindo automaticamente a correção de caminhos de importação quando arquivos são movidos ou excluídos.
-  **Ponte entre Negócio e Código: Excelente desempenho na fase de** pré-desenvolvimento, transformando requisitos vagos em métricas técnicas acionáveis (latência, throughput) e gerando diagramas de arquitetura (Mermaid/PlantUML) coerentes.
-  **Comandos de Slash Eficientes: O uso de / review, / test e / fix agiliza** tarefas repetitivas e padroniza a qualidade das entregas técnicas através de revisões automáticas.
-  **Orientação a Padrões de Design: Sugere proativamente a aplicação de** padrões como Strategy e Clean Architecture, alinhando o desenvolvimento às melhores práticas da engenharia de software.

### Limitações

-  **Intervenções Não Solicitadas: No uso do comando @workspace, a IA pode** ocasionalmente realizar alterações em arquivos que não foram explicitamente mencionados na tarefa (ex.: modificação automática em app.py), exigindo supervisão do desenvolvedor.
-  **Dependência de Contexto Explícito: Embora seja potente, a eficácia do** comando /review ou /test depende muito de o desenvolvedor referenciar corretamente os arquivos com ®, caso contrário, a análise pode ser limitada ao arquivo aberto.
-  **Interrupção de Fluxo em Revisões: Em alguns momentos, a ferramenta** pode indicar que o trabalho foi "parado" ou exigir que o usuário forneça novos exemplos para continuar uma revisão longa de múltiplos arquivos.
-  **Viés de Ecossistema: As sugestões arquiteturais tendem a ser fortemente** voltadas para serviços gerenciados da AWS (Lambda, DynamoDB), o que pode ser um ponto negativo para projetos que buscam agnostia de nuvem.

# 8. Riscos, Custos e Considerações de Uso

-  **Dependência de Vendor (Lock-in): Existe um risco elevado de dependência** do ecossistema AWS, uma vez que as sugestões de arquitetura e infraestrutura (IaC) são fortemente enviesadas para serviços como Lambda, DynamoDB e Bedrock.
-  **Custos Recorrentes: Enquanto o nível Free é útil para testes, o uso** profissional em larga escala exige a subscrição Pro de US$ 19/mês por **utilizador, o que pode tornar-se um custo fixo significativo para equipas** grandes.
-  **Barreiras Técnicas de Adoção: A ferramenta exige o uso de IDEs** específicas (VS Code ou JetBrains) e uma conta AWS ativa, o que pode limitar a adoção em ambientes que utilizam outras ferramentas de desenvolvimento.
-  **Restrições para Fine-tuning ou RAG: O suporte total para personalização** com dados do cliente (Fine-tuning) e o uso avançado de bases de conhecimento são funcionalidades restritas à versão paga (Pro), limitando a eficácia da ferramenta no nível gratuito.

# 9. Conclusão Geral da Análise

-  **A ferramenta é adequada para quais atividades de ES? O Amazon Q** Developer mostrou-se extremamente versátil em quase todo o ciclo de vida (SWEBOK). É particularmente forte na Elicitação e Análise de Requisitos, **Arquitetura (pelo suporte a diagramas e padrões) e Construção de** **Software (debugging e geração de testes).**
-  **Em quais casos deve ser evitada? Deve ser evitada em projetos que** exigem total agnostia de nuvem (onde o viés AWS pode atrapalhar) ou em organizações com restrições severas ao processamento de código em nuvens públicas por terceiros.
-  **Em qual maturidade técnica ela se encontra? A ferramenta encontra-se** numa fase de maturidade elevada, especialmente após a integração com os modelos Claude 3.5. Demonstra uma capacidade de raciocínio superior a simples geradores de código, conseguindo identificar falhas lógicas e contradições documentais.
-  **Vale a pena para a organização? Sim, principalmente se a organização já** utiliza a infraestrutura AWS. O ganho de produtividade no bootstrapping de projetos (estimado em ~70%) e a redução de erros lógicos críticos através do comando / review justificam o investimento na versão Pro.

# 10. Referências e Links Consultados

-  **Página Principal e Recursos do Amazon Q Developer:** https://aws.amazon.com/q/developer/
-  **Documentação de Modelos no AWS Bedrock (Claude 3.5 Sonnet):** https://aws.amazon.com/bedrock/claude/
-  **Guia de Usuário - Comandos e Funcionalidades:** https://docs.aws.amazon.com/amazona/latest/qdeveloper-ug/software-development-commands.html
-  **Tabela de Preços e Comparação de Planos (Free vs Pro):** https://aws.amazon.com/q/developer/pricing/
