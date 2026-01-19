#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          |            Codeium (Plugin)                / Windsurf (IDE AI-Native).                                                                    |
| **Fabricante / Comunidade**     |      Codeium (antiga Exafunction).                                                                             |
| **Site oficial / documentação** |           https://codeium.com                                                / https://windsurf.com                                                                                                     |
| **Tipo de ferramenta**          |IDE Híbrida com Agentes (Windsurf) e Assistente de Código (Plugin).|
| **Licença / acesso**            | Híbrido (Plugin VsCode é gratuito, mas IA é fechada (SaaS))        .                  |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                | Descrição                                                    |
|-------------------------------------|--------------------------------------------------------------|
| **Tipo de IA Generativa**           | Híbrido: LLM Multimodal + Agentes (Cascade)          |
| **Nome do Modelo***                  |**Agentes(Cascade):** SWE-1.5 - Claude Sonnet 4.5 - Claude Sonnet 4.5 (Thinking) - Claude Opus 4.5 - Claude Opus 4.5 (Thinking) - Claude Haiku 4.5 - Gemini 3.0 Pro (low) - Gemini 3.0 Pro (high) - GPT-5.2 (No Reasoning) - GPT-5.2 (Low Reasoning) - GPT-5.2 (Medium Reasoning) - GPT-5.2 (High Reasoning) - GPT-5.2 (Extra High Reasoning) - GPT-5.2 (No Reasoning Fast) - GPT-5.2 (Low Reasoning Fast) - GPT-5.2 (Medium Reasoning Fast) - GPT-5.2 (High Reasoning Fast) - GPT-5.2 (Extra High Reasoning Fast) - GPT-5.1 (No Reasoning) - GPT-5.1 (Low Reasoning) - GPT-5.1 (Medium Reasoning) - GPT-5.1 (High Reasoning) - GPT-5.1 (No Reasoning Fast) - GPT-5.1 (Low Reasoning Fast) - GPT-5.1 (Medium Reasoning Fast) - GPT-5.1 (High Reasoning Fast) - GPT-5.1-Codex - GPT-5.1-Codex Mini - GPT-5 (Low Reasoning) - GPT-5 (Medium Reasoning) - GPT-5 (High Reasoning) - GPT-5-Codex - SWE-1 - Gemini 2.5 Pro - Claude Opus 4.1 - Claude Opus 4.1 (Thinking) - xAI Grok Code Fast - Kimi K2 - Qwen3-Coder Fast - Qwen3-Coder - o3 - o3 (high reasoning) - Claude 3.7 Sonnet - Claude 3.7 Sonnet (Thinking) - Claude Sonnet 4 - Claude Sonnet 4 (Thinking) - gpt-oss 120B (Medium) - GPT-4o - GPT-4.1 - Claude 3.5 Sonnet - Claude 4 Opus - Claude 4 Opus (Thinking) - DeepSeek-V3-0324 - DeepSeek-R1 **Autocomplete:** Codeium Proprietary Model.|
| **Versão***                          | Cascade 2.0 / SWE 1.5                                                             |
| **Tamanho (nº de parâmetros)***      | Não disponível.|
| **Acesso***                          | API Comercial (SaaS) ou Enterprise Self-Hosted (Binário fechado)
| **Suporte a Fine-tuning***           | Sim (Limitado a contexto/RAG na versão Enterprise; não treina pesos).
| ***Suporte a RAG**                   | Sim                                .        |
| **Métodos de prompting suportados*** | CoT, ReAct, Self-Refine e Tool Use.
| **Ferramentas adicionais***          | Integração MCP, Super-tether, DeepWiki.    |


---


# 3. Contexto de Execução

| Item                                  | Descrição                               |
|---------------------------------------|-----------------------------------------|
| ***Onde roda?**                        |Híbrido: Cliente Local + Inferência em Nuvem (SaaS) ou Cluster Local (Enterprise).|
| **Infraestrutura utilizada no teste*** | Cliente: PC/Notebook padrão (CPU convencional). Backend: Cluster SaaS proprietário (GPUs otimizadas para baixa latência).   |
| ***Custos (quando aplicável)**         | Gratuito para indivíduos; Licença por usuário para times (SaaS); Enterprise (Custom) |

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
| Elicitação              |           Alto            |Gerou lista coerente de requisitos funcionais e não-funcionais para domínio específico, servindo como base sólida (draft) para analistas.                          |
| Análise                 |          Médio             |      Consegue derivar entidades a partir de requisitos textuais, mas pode misturar conceitos funcionais com não-funcionais.                 |
| Priorização             |              Alto         | Soube separar prioridades críticas de acessórias de acordo com o contexto do teste apresentado (seguindo o método MoSCoW)                          |
| Modelagem               |     Alto                  |Gerou código Plantuml sintaticamente correto a partir de descrição textual, permitindo visualização imediata de diagramas de classe.                          |
| Validação / Verificação |                Alto       | Foi capaz de encontrar irregularidades sutis em cenários hipotéticos                          |
| Documentação            |Alto                       |            A capacidade de gerar diagramas como código facilita a manutenção da documentação junto ao repositório.              |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais |        Medio               |É capaz de alterar código e seguir bons padrões, mas requer constante supervisão humana diante de possíveis erros de sintaxe e lógica.                    |
| Decisões arquiteturais           |Medio                       |Teoricamente preciso, mas carece de precisão na implementação.                          |
| Avaliação de trade-offs          |Genérico/Medio                       |Tende em apresentar alucinações, comentendo erros semânticos e ignorando detalhes específicos relevantes. No campo geral, performa de forma mediana.                          |
| Uso de padrões arquiteturais     |                  Sim     | Mas requer revisão humana.                          |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto |               Sim        |Capaz de sujerir Design Patterns, embora com erros de sintaxe                          |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Sim                      |Autocomplete eficiente e com baixa latência.                          |
| Refatoração       |              Excelente         |Otimizou uma função recursiva de forma eficiente em complexidade de tempo e de espaço.                          |
| Detecção de bugs  |      Sim/Medio                 |Comando /fix funcional, entretanto, não consegue corrigir erros próprios em funções/algorítimos complexos, necessitando de supervisão humana.                           |
---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) |           Risco            |Capaz de gerar testes que cobrem casos de borda de forma precisa, entretanto, peca em analisar a estrutura do código testado, alucinando e buscando valores que seriam impossíveis diante da natureza do código.                           |
| Execução de testes automatizados                 |      N/A                 |Não é capaz de gerar testes automatizados.                          |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Bom                      |Foi capaz de gerar pipelines YAML corretos, lógicos e seguros (github actions).                          |
| Automação                         |Bom / Médio                       |Funcional, mas necessita de sueprvisão humana.                          |
| Monitoramento                     |Bom Genérico                        |Ao testar a observabilidade, concluí que a solução proposta foi funcional, mas não a mais otimizada.                          |
| Documentação técnica automatizada |                  Bom     |Detalhou um pipeline CI/CD linha a linha.                          |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas |            Sim             |Na IDE Windsurf (IDE própria do Codeium) essas correções ocorrem de forma mais profunda por meio do agente Cascade. No VS Code, entretanto, a funcionalidade se mantém presente.                          |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        |        Bom               |Gerou um plano para um sprint de 2 semanas, dividindo corretamente tarefas de Frontend, Backend e DB. Limitação: Focou apenas no "caminho feliz", esquecendo tarefas de infraestrutura e setup inicial.                          |
| Execução                            |            Medio            | Foi capaz de seguir o plano criado para a execução do projeto proposto. Ela atriuiu funções, prazos e definiu prioridades com precisão.                          |
| Controle                            |           Medio            |Fez sugestões genéricas para garantir que a operação ocorresse de forma precisa.                          |
| Encerramento                        |         Bom              |Gerou um Release Note profissional, com linguagem adequada para o negócio. É importante analisar que, no teste, o Codeium avaliou as limitações que foram encontradas no processo proposto e no plano executado.                        |
| Gestão de riscos                    |            Bom           |         Capaz de identificar certas irregularidades e riscos no plano proposto.                 |
| Estimativas (tempo, custo, esforço) | Bom                       | Consegue fazer estimativas conservadoras levando em base o nível de instrução, senioridade, recursos, possíveis contratempos e horas dedicadas. Não consegui averiguar empiricamente se as análises estariam corretas, mas não são valores que fogem do padrão do mercado.                          |
| Medição                             | Medio                       |Capaz de avaliar bem as atividades propostas, entretando, alucina e esquece de cumprir com requisitos específicos de avaliação em certos casos.                          |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐            | Erra por esquecer detalhes ou, as vezes, simplesmente não conseguir realizar a atividade proposta.             |
| Profundidade técnica                | ⭐⭐⭐⭐            |Em relação à sintaxe e uso de tecnologias, foi preciso.             |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            |Seu maior ponto forte é justamente a capacidade de compreender todo o contexto da aplicação (RAG), reletindo isso até nas tarefas de autocomplete e geração de código.             |
| Clareza                             | ⭐⭐⭐⭐⭐            |Didática e clara em todas as atividades propostas. As respostas chegam a parecer que foram formuladas para facilitar tal compreensão. Além disso, possui funcionalidade para explicar o código gerado / pré-existente.              |
| Aderência às melhores práticas      | ⭐⭐⭐⭐            |Toma decisões estranhas quanto à lógica de funções e o uso de métodos/tecnologias que não são as melhores disponíveis, prezando mais pela clareza do que pela performance.              |
| Consistência entre respostas        | ⭐⭐⭐⭐            |Consistentes e coerentes umas com as outras. As vezes comete erros semãnticos.             |
| Ocorrência de alucinações           | Média |Alucina bastante na geração de código e de testes. Não tanto em tarefas de gestão.             |

---

  # **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

No total, foram realizados 16 experimentos cobrindo o ciclo de vida de desenvolvimento (SWEBOK), divididos em fases de complexidade crescente.

* **Produtividade e Contexto:**
    * Implementação de Árvore Binária para medir latência de autocomplete.
    * Verificação de RAG (*Context Awareness*) lendo definições em arquivos fechados.

* **Segurança e Riscos:**
    * Tentativa de indução de ataque *Supply Chain* (sugestão de bibliotecas falsas).

* **Engenharia Avançada e Migração:**
    * Tradução de código legado (C++ para Python).
    * Otimização algorítmica de Fibonacci ($O(2^n) \to O(n)$).
    * Implementação de padrão de Arquitetura (Injeção de Dependência).

* **Requisitos e Modelagem:**
    * Elicitação de requisitos para um Sistema de Aluguel.
    * Geração de diagrama de classes com Plantuml.
    * Aplicação do método MoSCoW (Priorização).
    * Validação cruzada de requisitos conflitantes (Anonimato vs Compliance Fiscal).

* **Arquitetura e Decisões:**
    * Análise de trade-offs entre Monolito e Microserviços (Latência e Custo).

* **Qualidade e Testes:**
    * Geração de testes unitários com Pytest (Border Cases para uma função fibonacci otimizada com DP em Python).

* **Operações e DevOps:**
    * Criação de Dockerfile.
    * Pipeline CI/CD para GitHub Actions.
    * Implementação de Observabilidade (Logs JSON + Prometheus).

* **Gestão e Métricas:**
    * Planejamento de Sprint.
    * Planejamento de execução e gestão do Sprint.
    * Encerramento e Release Notes.

### ● Resultados quantitativos

Os resultados indicam uma ferramenta de alta precisão sintática, mas que carece de visão sistêmica em tarefas de validação e arquitetura.

* **Acertos de Sintaxe:** 100% em códigos Python, YAML e Plantuml simples.
* **Velocidade:** Autocomplete com latência imperceptível (<50ms subjetivos) e resposta de chat rápida.
* **Falhas de Segurança:** 1 crítica (Docker executando como root).
* **Erros Semânticos/Lógicos:** 2 significativos (Inversão de conceito "maximizar latência" e Testes que esperam erros inexistentes).


### ● Exemplos

#### 1. Validação de Requisitos (Sucesso - Detecção de Conflito)
A ferramenta identificou corretamente a inviabilidade de dois requisitos conflitantes.

> **Prompt:** "O sistema deve garantir anonimato total... e emitir nota fiscal com CPF."

**Resposta da IA:**
> "Existem problemas de consistência e viabilidade... Garantir anonimato total pode ser um desafio... a emissão de nota fiscal com CPF pode exigir a coleta e armazenamento de informações sensíveis, o que pode violar a privacidade."

#### 2. Alucinação Lógica em Testes Unitários (Teste D - Falha)
A IA gerou um teste que falha na execução porque "alucina" que o código tem validações que não existem ("Wishful Testing").

```python
# Código Gerado pela IA (Pytest)
def test_fibonacci_otimizado():
    # ...
    # Test with negative numbers
    with pytest.raises(ValueError): # ALUCINAÇÃO: O código original NÃO levanta este erro
        fibonacci_otimizado(-1)
```

#### 3. Erro Semântico em Arquitetura (Teste C - Falha)
Ao comparar arquiteturas, a IA cometeu um erro grave de terminologia na conclusão.

**Resposta da IA:**
> "Em resumo, se o seu objetivo é maximizar a latência $$ERRO$$ e minimizar o custo de infraestrutura, uma arquitetura Monolítica Modular pode ser mais adequada..."

*(Nota: O objetivo correto seria "minimizar a latência". A IA inverteu o sentido.)*

#### 4. DevOps: Dockerfile Funcional mas Inseguro (Teste F - Risco)
A ferramenta aplicou boas práticas de cache, mas falhou na segurança básica.

```dockerfile
# Stage 1: Build (Correto uso de cache e multi-stage)
FROM python:3.9-slim AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# ...
# Stage 2: Final (Falha de Segurança: Roda como Root por padrão)
FROM python:3.9-slim
COPY --from=builder /app/dist /app
CMD ["./run.sh"]
```

#### 5. Sucesso em CI/CD (Teste G - Sucesso)
Gerou um pipeline YAML perfeito e seguro, usando actions oficiais.

```yaml
name: Test and Lint
on:
  push:
    branches: [ main ]
jobs:
  test-and-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest
      - run: flake8 .
```

---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* **Context Awareness (RAG):** Alta capacidade de ler e entender o projeto inteiro, não apenas o contexto local (arquivo aberto).
* **Velocidade e Produtividade:** Autocomplete extremamente rápido e refatoração algorítmica competente.
* **Documentação e Explicação:** Excelente em explicar código legado, gerar diagramas e redigir documentos técnicos.
* **DevOps Básico:** Gera pipelines de CI/CD (GitHub Actions) com perfeição.

    É importante apontar que o Codeium (Windsurf) lidou extremamente bem com tarefas de codificação no geral, com o RAG demonstrando ser realmente o ponto forte da IA (assim como prometido na documentação oficial). 

    Quando estava preparando testes lógicos utilizando um algorítimo de busca por caminhos mínimos em grafos -- o Dijkstra -- o Codeium estava autocompletando as funções com base em outros códigos meus que estavam numa pasta sem nenhuma ligação com o repositório no qual eu estava fazendo os testes, evidenciando a altíssima capacidade da IA realizar pesquisas profundas em todas as pastas do computador em busca de contexto e dados para realizar um autocomplete preciso. 

### **Limitações**

* **Análise Métrica:** Incapaz de realizar análises quantitativas com precisão.
* **Coerência de Testes:** Gera testes para a versão "ideal" do código, que falham na versão "real".
* **Segurança:** Tende a gerar configurações inseguras se não for explicitamente guiada.
* **Senioridade:** Conhece os conceitos, mas falha na implementação detalhada e na avaliação de trade-offs específicos.

    Em resumo, é importante salientar que a IA necessita de supervisão humana para **toda** atividade que envolva um certo nível de complexidade e/ou possua muitas variáveis a serem consideradas.

---

#  **8. Riscos, Custos e Considerações de Uso**

* **Caixa preta:** O modelo é proprietário e o funcionamento interno do "Cascade" não é auditável.
* **Privacidade:** O código é enviado para a nuvem da Codeium para inferência (na versão SaaS gratuita/pro). Exige versão Enterprise (Self-hosted) para compliance rigoroso.
* **Risco de senioridade:** O código gerado funciona, mas pode conter débitos técnicos que um mais inexperiente não notaria. Exige revisão.
* **Barreiras de Adoção:** Baixíssima. A instalação do plugin ou da IDE Windsurf é imediata.

---

#  **9. Conclusão Geral da Análise**

* **Adequação:** A ferramenta é altamente adequada para aumentar a produtividade individual (codificação, boilerplate, documentação, diagramas) e para tarefas de DevOps padronizadas (CI/CD).
* **Evitar:** Não deve ser utilizada sem supervisão para decisões de Arquitetura Crítica, análise de métricas ou segurança de infraestrutura.
* **Maturidade Técnica:** Resolve bem o "como fazer", mas precisa de ajuda no "o que e porquê fazer".
* **Vale a pena?** Sim, o ganho de velocidade na escrita de código e documentação supera os riscos, revisão humana.

---

#  **10. Referências e Links Consultados**

* [Codeium Documentation](https://docs.codeium.com)
* [Windsurf IDE](https://windsurf.com)
* SWEBOK Guide v3.0.
* Documentação oficial do PlantUml e GitHub Actions.