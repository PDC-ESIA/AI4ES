# Resultados dos Testes — Integração TACO (workflow_taco)

**Responsável:** Time 4 — Codificação  
**Contexto:** Registro dos testes realizados na PoC de integração do TACO ao pipeline PDC, com adaptadores de entrada e saída para os agentes coder(cenário 1) e reviewer(cenário 2) sem modificação dos agentes existentes.

---

## 1. O que foi implementado

Criado o módulo `adk/src/agents/workflow_taco/` com os seguintes componentes:

| Módulo | Papel |
|---|---|
| `agent.py` | Orquestrador principal: `TacoAgent` (dispatcher), `TacoGabaritoAgent` (Cenário 1), `TacoReviewAgent` (Cenário 2) |
| `task_builder/` | `LlmAgent` que traduz JSON TACO → instrução para o `cr_coder_agent` |
| `result_composer/` | `LlmAgent` que consolida os arquivos gerados + resultado da validação em gabarito formatado |
| `review_builder/` | `LlmAgent` que traduz JSON TACO + código do aluno → instrução para o `cr_review_analyzer_agent` |
| `feedback_composer/` | `LlmAgent` que filtra e transforma a revisão SDLC em feedback pedagógico para o aluno |
| `matching.py` | Cascata determinística (exato → fuzzy → posicional) que encontra o `.py` de cada variação no workspace |
| `validator.py` | Valida sintaxe e executa `challenge.examples` via `subprocess.run` com input via stdin |

**Agentes SDLC utilizados sem modificação:**
- `workflow_coding_review/coder/agent.py` → chamado via `Runner` isolado no Cenário 1
- `workflow_coding_review/reviewer/agent.py` → chamado via `Runner` isolado no Cenário 2

**Nenhuma linha dos agentes existentes foi alterada.**

---

## 2. Ambiente de testes

- ADK versão: 1.33.0
- Comando de execução: `python -m google.adk.cli web src/agents` (dentro de `adk/`)
- Interface: ADK Web UI local (`http://localhost:8000`)
- Agente selecionado: `workflow_taco`
- Modelo LLM: `gpt-4` (GitHub Copilot)

---

## 3. Testes realizados

Todos os testes foram realizados via ADK Web UI. Os JSONs de entrada foram fornecidos pelo time TACO.

---

### Teste 1 — Cenário 1, exercício simples (001.json)

**Exercício:** Soma de Dois Inteiros  
**Variações:** 2 (`leitura-direta`, `com-funcao-e-tipagem`)  
**`challenge.examples`:** ausente no JSON

**Resultado:**
- `task_builder`: gerou instrução de implementação com as 2 variações e o contrato de interface
- `cr_coder_agent`: gerou os arquivos `leitura_direta.py` e `com_funcao_e_tipagem.py`
- `matching`: encontrou os 2 arquivos por correspondência exata de slug
- `validator`: validação sintática OK para ambos; sem exemplos para executar
- `result_composer`: produziu gabarito com os dois códigos, estratégias descritas em português, e nota de ausência de `challenge.examples`

**Status:** concluído sem erros.

---

### Teste 2 — Cenário 1, exercício de média complexidade (054.json)

**Exercício:** exercício com 3 variações algorítmicas distintas  
**Variações:** 3  
**`challenge.examples`:** ausente no JSON

**Resultado:**
- Os 3 arquivos foram gerados e identificados pelo matching
- Validação sintática OK para os 3
- `result_composer` produziu gabarito com os três códigos e resumos pedagógicos

**Status:** concluído sem erros.

---

### Teste 3 — Cenário 1, exercício com `challenge.examples`

**Exercício:** exercício com campo `challenge.examples` preenchido (6 exemplos de entrada/saída)  
**Variações:** 2

**Resultado:**
- `validator` executou cada variação contra os 6 exemplos via `subprocess.run` com stdin simulado
- **6/6 exemplos passaram** para ambas as variações
- `result_composer` listou cada exemplo com status `PASSOU`, stdin e stdout

```
[PASSOU] entrada='3 5' esperado='8' obtido='8'
[PASSOU] entrada='0 0' esperado='0' obtido='0'
[PASSOU] entrada='-1 1' esperado='0' obtido='0'
[PASSOU] entrada='10 20' esperado='30' obtido='30'
[PASSOU] entrada='100 200' esperado='300' obtido='300'
[PASSOU] entrada='-5 -3' esperado='-8' obtido='-8'
```

**Status:** concluído sem erros. Validação de exemplos funcionando corretamente.

---

### Teste 4 — Cenário 2, código do aluno correto

**Exercício:** mesmo exercício do Teste 1 (001.json)  
**Código do aluno:** implementação correta usando `input()` e `print()`

**Resultado:**
- `review_builder` formatou o contexto para o reviewer SDLC
- `cr_review_analyzer_agent` executou análise estática (Ruff + Bandit) e revisão
- `feedback_composer` filtrou a saída SDLC e produziu feedback pedagógico

**Conteúdo do feedback gerado:**
- Identificou corretamente que o código resolve o enunciado
- Apontou pontos positivos (leitura correta de stdin, uso de `map` e `split`)
- Não propagou ruídos SDLC (ausência de testes, PLAN.md) para o aluno
- Sugeriu próximos passos de estudo

**Status:** concluído. Feedback pedagogicamente adequado para o contexto.

---

### Teste 5 — Cenário 2, código do aluno com bug

**Exercício:** mesmo exercício do Teste 1 (001.json)  
**Bug introduzido:** leitura dos números em duas linhas separadas (`input()` + `input()`) em vez de uma linha com `split()`, violando o contrato stdin do enunciado

**Resultado:**
- `cr_review_analyzer_agent` identificou a inconsistência com o contrato de entrada
- `feedback_composer` traduziu o achado do SDLC para linguagem pedagógica
- Feedback explicou ao aluno por que a leitura está incorreta e como o Pyodide simula stdin

**Status:** concluído. Bug identificado corretamente e comunicado de forma construtiva.

---

## 4. Observações técnicas registradas

Esta seção documenta comportamentos observados nos logs durante os testes.

### 4.1 Número de chamadas LLM por exercício

**Cenário 1 — logs observados durante o Teste 1:**
```
[TACO] Passo 1/4 — task_builder         → 1 chamada LLM
[TACO] Passo 2/4 — coder
  LiteLLM completion() model=gpt-4      → chamada 1 (context_engineer)
  LiteLLM completion() model=gpt-4      → chamada 2 (planejamento SDLC)
  LiteLLM completion() model=gpt-4      → chamada 3 (geração de código)
  LiteLLM completion() model=gpt-4      → chamada 4 (iteração/revisão)
[TACO] Passo 3/4 — matching + validação → sem LLM (determinístico)
[TACO] Passo 4/4 — result_composer      → 1 chamada LLM
```

Total observado: **6 chamadas LLM** para o exercício mais simples (2 variações).

**Cenário 2 — log análogo:**  
`review_builder` (1) + pipeline do reviewer SDLC (2–3) + `feedback_composer` (1) = **4–5 chamadas LLM**.

### 4.2 Artefatos gerados pelo `cr_coder_agent` no workspace

Após cada execução do Cenário 1, o diretório `workspace_output/coder/src/` continha:

```
workspace_output/coder/src/
├── leitura_direta.py          ← usado pelo matching → enviado ao result_composer
├── com_funcao_e_tipagem.py    ← usado pelo matching → enviado ao result_composer
├── PLAN.md                    ← ignorado pelo matching (não é .py)
├── run.json                   ← ignorado pelo matching (não é .py)
└── README.md                  ← ignorado pelo matching (não é .py)
```

Os três artefatos (`PLAN.md`, `run.json`, `README.md`) foram gerados porque o system prompt do `cr_coder_agent` os declara como obrigatórios. O `task_builder` instrui o coder a não criar esses artefatos, mas a instrução de turno compete com o system prompt — este tem precedência. Os artefatos são descartados pelo `matching.py` sem impacto no resultado final, mas foram gerados e consumiram tokens.

### 4.3 Workspace compartilhado entre Cenário TACO e pipeline SDLC

O `cr_coder_agent` e o `cr_review_analyzer_agent` utilizam `workspace_output/coder/src/` — o mesmo diretório do pipeline SDLC. O `agent.py` executa `_limpar_workspace_coder()` antes de cada chamada TACO, o que garante isolamento entre exercícios TACO executados sequencialmente.

O comportamento em execuções simultâneas (dois exercícios TACO em paralelo, ou TACO + SDLC rodando ao mesmo tempo) não foi testado nesta PoC.

### 4.4 Filtragem pedagógica do `feedback_composer`

O `feedback_composer` recebe a saída bruta do reviewer SDLC — que pode conter issues como "ausência de suíte pytest", "violação de SRP" ou "PLAN.md não encontrado" — e filtra esses ruídos antes de apresentar ao aluno. Nos Testes 4 e 5, esse filtro funcionou: o feedback ao aluno não continha essas referências.

O filtro é implementado via instrução de prompt (lista de issues a ignorar/suavizar). A eficácia do filtro pode variar dependendo do exercício e do volume de ruído SDLC na saída do reviewer.

### 4.5 Análise estática no Cenário 2

O `cr_review_analyzer_agent` usa um `before_callback` (`_inject_static_findings`) que executa Ruff e Bandit no código presente em `workspace_output/coder/src/` antes de iniciar a revisão. Para que isso funcione no Cenário 2, o `agent.py` escreve o código do aluno em `student_solution.py` antes de invocar o reviewer. Essa etapa funcionou nos Testes 4 e 5.

---

## 5. Limitações documentadas no código-fonte

As seguintes limitações estão registradas no docstring do `agent.py` (transcrição direta):

> **1. System prompt SDLC imutável:** o coder é instruído a criar `PLAN.md`, `run.json` e `README` como obrigatórios. O `task_builder` instrui o contrário, mas o system prompt tem precedência sobre o turno do usuário.

> **2. Workspace compartilhado:** coder TACO e coder SDLC usam o mesmo diretório (`workspace_output/coder/src/`). O `agent.py` limpa antes de cada chamada TACO — aceitável para a PoC, bloqueante para produção concorrente.

> **3. `challenge.examples` ausente:** os 60 JSONs de produção não têm este campo. O validator detecta e loga como achado para o time TACO.

---

## 6. Sumário dos resultados

| Teste | Cenário | Resultado | Observação |
|---|---|---|---|
| 001.json — simples | 1 — Gabarito | Concluído | 2/2 variações geradas e identificadas |
| 054.json — médio | 1 — Gabarito | Concluído | 3/3 variações geradas e identificadas |
| Com `challenge.examples` | 1 — Gabarito | Concluído | 6/6 exemplos passaram na validação de execução |
| Código correto do aluno | 2 — Revisão | Concluído | Feedback pedagógico gerado sem ruído SDLC |
| Código com bug do aluno | 2 — Revisão | Concluído | Bug de contrato stdin identificado e comunicado |

**Todos os 5 testes concluíram com sucesso do ponto de vista funcional.**

---

## 7. Fatos registrados para análise posterior

Os itens abaixo são fatos observados durante os testes, registrados para subsidiar discussões de arquitetura sem antecipar conclusões:

1. **O `cr_coder_agent` executa o pipeline SDLC completo** (context engineering, planejamento, geração, iteração) para cada chamada TACO, independentemente da complexidade do exercício.

2. **Os artefatos SDLC (`PLAN.md`, `run.json`, `README.md`) são gerados e descartados** em toda execução do Cenário 1. Não afetam o resultado final, mas são parte do custo de execução.

3. **O workspace compartilhado não foi testado em concorrência.** O comportamento em execuções paralelas é desconhecido e não foi testado nesta PoC.

4. **A filtragem pedagógica do `feedback_composer` não foi testada com exercícios que gerem volume alto de ruído SDLC.** Os exercícios testados eram simples; exercícios com mais variações ou código mais complexo podem gerar mais issues SDLC a filtrar.

5. **O campo `challenge.examples` está ausente nos 60 JSONs de produção do TACO.** A validação de execução funcionou nos testes, mas não será ativada nos exercícios reais sem que esse campo seja adicionado.

6. **A instrução de turno do `task_builder` não sobrepõe o system prompt do `cr_coder_agent`.** Esse comportamento é esperado pelo design do ADK/LLM e está documentado no código.
