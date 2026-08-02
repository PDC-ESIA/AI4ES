# Planejamento da Implementação do Benchmark (Coder Agent)

Este documento descreve o planejamento arquitetural, as especificações e o plano de execução para a implementação do harness de benchmark modular e da suíte de análise estatística para o **Coder Agent**, isolados sob o diretório `benchmarks/construcao/`.

---

## 1. Objetivos do Benchmark

- **Avaliação de Desempenho:** Medir de forma robusta e automatizada a capacidade do Coder Agent de gerar código correto frente a desafios de programação clássicos (HumanEval e MBPP).
- **Consistência Estatística:** Mitigar a variabilidade inerente aos modelos de linguagem através de múltiplas execuções independentes ($N$ rodadas por tarefa) para cada modelo avaliado.
- **Análise Estatística Avançada:** Comparar múltiplos modelos de forma cientificamente rigorosa utilizando estatística não-paramétrica (Wilcoxon, Friedman, Nemenyi) e métricas de tamanho de efeito (Cliff's Delta, Kendall's W).
- **Execução Segura:** Avaliar o código gerado em ambiente isolado (sandbox local ou Docker) para evitar efeitos colaterais no sistema operacional hospedeiro.

---

## 2. Estrutura de Diretórios Proposta

O benchmark está estritamente isolado na seguinte estrutura para evitar conflitos de merge e poluição da raiz:

```text
benchmarks/
├── shared/
│   ├── __init__.py
│   └── statistical_treatment.py          # Funções utilitárias de estatística em Python/Numpy puro
└── construcao/
    ├── planejamento_implementacao.md     # Este arquivo de planejamento atualizado com as subfases
    ├── tarefas/
    │   ├── humaneval_subset.jsonl        # Subconjunto de 5 tarefas do HumanEval
    │   └── mbpp_subset.jsonl            # Subconjunto de 5 tarefas do MBPP
    ├── resultados/
    │   ├── exec_logs/                    # Logs JSON brutos de cada rodada/execução
    │   └── relatorios/                   # Relatórios consolidados e tabelas Markdown geradas
    └── scripts/
        ├── __init__.py
        ├── run_coder_benchmark.py        # Orquestrador do benchmark (carrega datasets, invoca o agente)
        ├── evaluate_sandbox.py           # Executor isolado das suítes de teste (Docker ou local)
        └── aggregate_results.py          # Consolidador e gerador da análise estatística final
```

---

## 3. Componentes Detalhados e Fluxo de Dados

O benchmark opera através de três scripts principais executados em sequência:

### A. Carregamento e Orquestração (`run_coder_benchmark.py`)
1. **Leitura dos Datasets:** Lê os arquivos `.jsonl` em `tarefas/`. Cada linha representa uma tarefa com:
   - `task_id`: Identificador único.
   - `prompt`: Instrução de codificação ou assinatura da função.
   - `test`: Conjunto de asserções em Pytest para validação da corretude.
2. **Integração com Coder Agent:**
   - Inicializa o Coder Agent localizado em `adk/src/agents/coder/agent.py`.
   - **Tratamento HITL (Crítico):** Para o benchmark automatizado, o loop interativo que exige confirmação humana ("sim/não") para commits do Git deve ser programaticamente desabilitado ou mockado.
3. **Loop de Execuções:**
   - Executa $N$ rodadas independentes para cada tarefa.
   - Mede o tempo de resposta, quantidade de tokens consumidos, custos de API e sucesso de compilação.
4. **Persistência de Logs:** Cada rodada gera um log bruto em formato JSON contendo o código gerado, os metadados e o resultado da execução.

### B. Sandbox de Execução Segura (`evaluate_sandbox.py`)
1. **Isolamento de Ambiente:**
   - Cria uma pasta temporária com a estrutura requerida pelo Pytest (`app/__init__.py`, `tests/__init__.py`, `conftest.py`).
   - Grava o código gerado em `app/main.py` e os testes em `tests/test_code.py`.
2. **Estratégias de Sandbox:**
   - **Docker Sandbox (Preferencial):** Instancia um container leve (`python:3.12-slim`), monta o diretório temporário, executa o pytest com `pytest-json-report` e extrai os resultados estruturados.
   - **Subprocesso Local (Fallback):** Executa o pytest localmente através de um subprocesso isolado com timeout de segurança (ex: 5 segundos) para precaver loops infinitos.
3. **Métricas de Retorno:** Retorna se o código compilou, se todos os testes passaram, a quantidade total de testes, testes passados e logs detalhados de falhas de asserção ou sintaxe.

### C. Consolidação e Estatística (`aggregate_results.py`)
1. **Cálculo de Pass@k:** Estima a probabilidade de aprovação de pelo menos um código gerado se selecionados $k$ de forma aleatória, seguindo a fórmula matemática clássica:
   $$Pass@k = 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}$$
   Onde $n$ é o total de rodadas e $c$ é a quantidade de rodadas com sucesso.
2. **Estatísticas Descritivas:** Média, mediana, desvio padrão, mínimos, máximos e intervalo de confiança de 95% para tempos de execução e contagem de tokens.
3. **Testes de Hipótese (Sem Scipy):**
   - **Comparação entre Dois Modelos (Wilcoxon Signed-Rank & Cliff's Delta):** Testa se a diferença de performance entre dois modelos é estatisticamente significativa e calcula a magnitude dessa diferença.
   - **Comparação de Múltiplos Modelos (Friedman & Nemenyi):** Aplica o teste global de Friedman para detectar se há diferenças de ranking e, se positivo, calcula a Diferença Crítica (CD) de Nemenyi para identificar pares significativamente distintos.
   - **Concordância (Kendall's W):** Mede o grau de associação ou concordância entre o desempenho dos modelos através das tarefas do benchmark.

---

## 4. Plano de Desenvolvimento em Subfases (Incremental)

Para mitigar riscos, isolar a complexidade de cada especificação e garantir qualidade, o desenvolvimento do esforço de benchmark é dividido em subfases dedicadas para cada dataset de forma isolada e sequencial:

### 🔹 Subfase 1: Suíte de Base e Infraestrutura Estatística (Concluída)
*   **Foco:** Criação do diretório estruturado, isolamento de dependências e desenvolvimento do motor matemático (`statistical_treatment.py`) em Python puro.

### 🔹 Subfase 2: Vertente HumanEval (Próximo Passo)
*   **Parsing:** Implementar e validar a leitura correta das tarefas de `humaneval_subset.jsonl`.
*   **Orquestração:** Integrar o Coder Agent com foco na assinatura e docstrings do HumanEval.
*   **Sandbox:** Validar o isolamento e execução das funções geradas.
*   **Resultado:** Dry-run completo e geração dos logs de execução (`resultados/exec_logs/`) focados unicamente no HumanEval.

### 🔹 Subfase 3: Vertente MBPP
*   **Parsing:** Adaptar o orquestrador para ler a estrutura de asserções curtas do `mbpp_subset.jsonl`.
*   **Orquestração:** Configurar prompts e o Coder Agent para lidar com as instruções do MBPP.
*   **Sandbox:** Ajustar a injeção dinâmica de importação e asserts rápidos.
*   **Resultado:** Dry-run completo e logs de execução do MBPP salvos de forma independente.

### 🔹 Subfase 4: Consolidador de Análise Estatística (Pass@k e Testes de Hipótese)
*   **Foco:** Leitura de todos os logs JSON consolidados de ambas as fases anteriores.
*   **Operações:** Execução dos cálculos de `Pass@k` para ambos os datasets, aplicação dos testes descritivos, Wilcoxon/Friedman, e exportação automática do relatório final consolidado em `resultados/relatorios/relatorio_final.md`.

### 🔹 Subfase 5 (Futura/Opcional): Expansão para Benchmarks Avançados
*   *Plug-and-play* individual para cada benchmark opcional aprovado (EvalPlus, LiveCodeBench, BigCodeBench), reusando a mesma sandbox e agregador estatístico já consolidados.
