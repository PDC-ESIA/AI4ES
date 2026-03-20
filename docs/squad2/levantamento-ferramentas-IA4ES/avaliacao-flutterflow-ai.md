# 1. Identificação da Ferramenta

| Item                             | Descrição                                                                       |
| --- | --- |
| *Nome da ferramenta*           | FlutterFlow AI App Generator                                                                    |
| *Fabricante / Comunidade*     | FlutterFlow, Inc.                                                                     |
| *Site oficial / documentação* | [FlutterFlow AI](https://www.flutterflow.io/ai) / [Flutter flow Docs](https://docs.flutterflow.io/)                                                                           |
| *Tipo de ferramenta*           | Plataforma Low-Code com assistente de IA para geração de UI (layouts) e lógica (Dart).   |
| *Licença / acesso*             | Comercial (Planos Free, Pro e Teams). Uso de IA disponível no plano gratuito para testes, com limite de 5 gerações/mês.                                   |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                 | Descrição                                                     |
| --- | --- |
| *Tipo de IA Generativa*           | Baseada em LLM.                         |
| *Nome do Modelo*                   | Não divulgado. |
| *Versão*                           | Não divulgado.                                                             |
| *Tamanho (nº de parâmetros)*       | Não divulgado.                                           |
| *Acesso*                           | Integrado na IDE Web (O usuário interage via prompts nos painéis "Generate with AI").                           |
| *Suporte a Fine-tuning*           | Não exposto ao usuário.                     |
| *Suporte a RAG*                   | Não aplicável/não configurável diretamente (no escopo do teste).                                                       |
| *Métodos de prompting suportados* | Linguagem Natural, Upload de Imagens (Screenshot-to-Code) e integração Figma.                        |
| *Ferramentas adicionais*           | AI Agents (para o produto final, não disponível no plano gratuito).  |

---

# 3. Contexto de Execução

| Item                                   | Descrição                               |
| --- | --- |
| *Onde roda?*                         | **Híbrido**. Design/Geração na Nuvem (Browser). Código gerado roda nativamente (Mobile/Web/Desktop).                 |
| *Infraestrutura utilizada no teste* | Navegador Web (Chrome). Processamento de IA server-side.     |
| *Custos (quando aplicável)*         | IA inclusa no plano grátis (uso limitado). |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              |         N/A           | A ferramenta não auxilia na coleta ou compreensão de requisitos.                         |
| Análise                 |         N/A           | Não há suporte à análise de requisitos funcionais ou não funcionais.                         |
| Priorização             |         N/A           | Nenhum mecanismo de apoio à priorização de requisitos é oferecido.                          |
| Modelagem               |         N/A           | Não gera modelos conceituais, de domínio ou requisitos.                          |
| Validação / Verificação |         N/A           | Não verifica consistência ou completude de requisitos.                          |
| Documentação            |         N/A           | Não produz documentação de requisitos de forma automatizada.                         |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais |         N/A           | A IA atua apenas no nível de UI e widgets, sem visão arquitetural do sistema.                          |
| Decisões arquiteturais           |         N/A           | Não sugere nem justifica decisões arquiteturais.                         |
| Avaliação de trade-offs          |         N/A           | Não há análise comparativa de alternativas técnicas.                         |
| Uso de padrões arquiteturais     |         N/A           | Segue padrões do framework Flutter (ex.: composição de widgets), porém sem explicitação ou escolha consciente de padrões arquiteturais.                         |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto |         N/A           | Embora o código gerado siga convenções básicas do Flutter, não há aplicação explícita ou justificável de padrões de projeto.                         |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código |Sim | Gera telas e modais completos via prompt. Gera funções customizadas e lógica de backend em Dart, requer prompts específicos, definição de variáveis de entrada e saída.                           |
| Refatoração       |         N/A           | Não oferece suporte à refatoração de código existente.                          |
| Detecção de bugs  |         N/A           | Não identifica erros lógicos, inconsistências ou problemas de integração.                         |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) |         N/A           | Não gera testes unitários, de integração ou de aceitação.                          |
| Execução de testes automatizados                 |         Sim           | Executa testes automatizados, mas apenas em planos pagos.                       |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             |         N/A           | Não integra pipelines de integração e entrega contínuas.                         |
| Automação                         |         N/A           | A automação é restrita à geração inicial de artefatos de UI.                         |
| Monitoramento                     |         N/A           | Não há suporte a observabilidade ou métricas de runtime.                         |
| Documentação técnica automatizada |         N/A           | Não gera documentação técnica do sistema.                         |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas |         N/A           | Não corrige código ou inconsistências de forma autônoma.                         |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        |         N/A           | Nenhum apoio a planejamento de atividades ou cronogramas.                         |
| Execução                            |         N/A           | Não acompanha progresso do projeto.                         |
| Controle                            |         N/A           | Não há métricas de controle ou indicadores.                         |
| Encerramento                        |         N/A           | Não oferece suporte a encerramento de projetos.                         |
| Gestão de riscos                    |         N/A           | Riscos não são identificados nem mitigados pela ferramenta.                         |
| Estimativas (tempo, custo, esforço) |         N/A           | Não estima esforço, custo ou tempo.                         |
| Medição                             |         N/A           | Não coleta métricas de processo ou produto.                         |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐            | A UI gerada é visualmente correta, porém frequentemente imprecisa em relação aos dados reais do domínio.             |
| Profundidade técnica                | ⭐⭐⭐            | Restrita ao ecossistema Flutter/Dart, sem abstrações de engenharia.             |
| Contextualização no código/problema | ⭐            | Falha crítica: ignora Data Types, variáveis e alterações manuais existentes no projeto.             |
| Clareza                             | ⭐⭐⭐⭐            | Interface de interação clara e respostas satisfatórias.             |
| Aderência às melhores práticas      | ⭐⭐⭐            | Segue padrões básicos do Flutter, mas sem aderência ao modelo de domínio.            |
| Consistência entre respostas        | ⭐⭐            | Resultados variam significativamente entre prompts semelhantes.             |
| Ocorrência de alucinações           | Média | Criação recorrente de campos genéricos não solicitados quando o prompt não é excessivamente específico.            |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

1. Geração de tela a partir de Data Type: criação do Data Type Departamento (id, nome, descrição) e solicitação de tela de cadastro.
2. Atualização incremental: adição manual de novo atributo e solicitação de modal de visualização.

### ● Resultados quantitativos

- Aderência ao modelo: 0%. Em ambos os casos, os campos definidos foram ignorados.
- Persistência de contexto: nula. Alterações manuais não foram consideradas.
- Qualidade do código: boa para scaffolding visual, acelerando a criação inicial de telas.

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Alta velocidade para geração de boilerplate visual.
* Integração imediata do código gerado à árvore de widgets.

### **Limitações**

* Falta de Consciência Sistêmica: A IA não analisa o estado atual do projeto (Data Types, Variáveis, APIs) antes de gerar novos itens.
* Overhead de Limpeza: O desenvolvedor gasta tempo significativo removendo campos "inventados" pela IA que não pertencem ao domínio.

---

#  **8. Riscos, Custos e Considerações de Uso**

* Custo de Supervisão: Requer validação manual constante para garantir que os campos de UI correspondam ao banco de dados.
* Risco de inconsistência cumulativa: o uso incremental da IA tende a degradar a coerência entre UI, Data Types e regras de negócio.

---

#  **9. Conclusão Geral da Análise**

* Adequação: Indicada para prototipagem visual rápida e construção de aplicativos.
* Evitar: Tarefas incrementais ou que dependam de consistência estrita com modelos de dados pré-existentes.
* Maturidade: média-baixa em termos de inteligência de projeto, atuando como AI-assisted UI scaffolding do que como um assistente consciente.

---

#  **10. Referências e Links Consultados**

- [FlutterFlow AI](https://www.flutterflow.io/ai)
- [Flutter flow Docs](https://docs.flutterflow.io/) 


# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

* [x] Tipo de interface: Chat, autocomplete, comandos ou agente?
    * Interface Visual (Drag-and-Drop) assistida por IA via painéis "Generate with AI" e importação de arquivos/Figma.


* [x] Integração: Funciona dentro do editor/IDE ou é ferramenta separada?
    * Ferramenta separada (IDE proprietária do Flutter Flow).


* [x] Facilidade inicial: Consegui usar nos primeiros 5 minutos sem tutoriais?
    * **Média**. Usar a IA para gerar a primeira tela é instantâneo e fácil. Porém, conectar os dados e configurar a navegação exige entender a lógica visual da ferramenta.



## 2. Contexto do Projeto

* [x] Lê arquivos automaticamente: Preciso colar código ou ela vê o projeto?
    * **Sim**. Capacidade de ler imagens e arquivos de design para converter em componentes funcionais.


* [x] Entende a stack: Detecta linguagens/frameworks ou preciso explicar tudo?
    * Sim. Especializado em Flutter (Frontend) e Dart (Lógica).


* [ ] Múltiplas linguagens: Funciona bem com mais de uma linguagem?
    * Não. Gera código exclusivamente em Dart (Flutter).


## 3. Modo de Trabalho

* [x] Nível de autonomia: Só sugere ou também modifica arquivos sozinha?
    * Apenas cria arquivos conforme solicitado.


* [x] Controle do usuário: Posso revisar antes de aceitar mudanças?
    * Sim. Permite preview e revisão do componente gerado pela IA antes da inserção definitiva no projeto.


* [x] Escopo das ações: Mexe em 1 arquivo por vez ou vários simultaneamente?
    * **Por Componente/Tela**. A IA atua no escopo da tela que está sendo desenhada ou da função que está sendo escrita.



## 4. Capacidades Observadas

* [x] Completude: Gera blocos inteiros de código ou apenas linhas soltas?
    * Gera blocos funcionais completos (Layouts + Funções Dart com imports).


* [ ] Explicação: Possui funcionalidade dedicada para explicar código (botão/comando)?
    * Não possui recurso nativo para explicar o código gerado via chat/botão.


* [x] Correção: Possui comandos explícitos de /fix ou "Debug this"?
    * Não possui comandos de debug/fix; foco estrito em criação/geração.


* [ ] Referências: Cita de onde tirou a informação (fontes) ou gera sem referência?
    * Não aplicável.



## 5. Limitações Importantes

* [x] Vinculada a plataforma específica: Força uso de serviços (ex: AWS, Azure)?
    * O FlutterFlow permite exportar o código fonte e continuar o desenvolvimento localmente, sem depender da plataforma para sempre. Entretanto, a funcionalidade de gerar componentes via IA é perdida fora da plataforma original.


* [x] Restrições de linguagem/stack: Tem tecnologias que não suporta bem?
    * Focado estritamente em Apps Mobile/Web via Flutter. Não serve para criar APIs de Backend complexas (Node.js/Python), apenas consome APIs.


* [x] Curva de aprendizado: Precisa de muito treino pra usar direito?
    * **Média**. A IA acelera o início (UI), mas dominar o gerenciamento de estado e banco de dados requer estudo.
