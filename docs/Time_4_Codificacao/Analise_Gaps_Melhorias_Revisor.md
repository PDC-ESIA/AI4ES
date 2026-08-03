# Análise de Gaps, Proposta de Melhorias e Tooling Open-Source — Agente Revisor

**Equipe:** Time 4 — Codificação  
**Escopo:** `workflow_coding_review` / `cr_reviewer`  
**Status:** Implementado (branch `feat/code/reviewer-static-analysis`)

---

## 1. Análise do Fluxo Atual

### Arquitetura vigente

O agente revisor (`cr_reviewer`) opera como um `SequentialAgent` com duas fases encadeadas:

```
[Coder Workspace]
       │
       ▼
┌─────────────────────┐
│   _review_analyzer  │  LlmAgent — lê arquivos do coder,
│                     │  produz análise em Markdown
└─────────────────────┘
       │ state["review_analysis"]
       ▼
┌─────────────────────┐
│  _review_persister  │  LlmAgent — salva o relatório
│                     │  via tool_salvar_relatorio
└─────────────────────┘
       │
       ▼
 verificacao_revisao.md
```

O `_analyzer` consome os arquivos produzidos pelo coder e produz uma análise em Markdown cobrindo 4 camadas: completude, arquitetura, corretude e testes. O `_persister` recebe essa análise via `output_key` e a persiste em disco.

### Fluxo de entrada

O revisor recebe indiretamente os artefatos do coder via workspace compartilhado. O `_CODER_WS` é inspecionado em tempo de invocação via `_discover_coder_files()`, que lista os arquivos disponíveis e os injeta no prompt do analyzer.

---

## 2. Gaps Identificados

### GAP-01 — Risco de "modo narrador" no `_persister` *(Severidade: Alta)*

O `_review_persister` é um `LlmAgent` cuja única função é chamar `tool_salvar_relatorio`. Por ser um LLM, existe o risco de ele **descrever** a chamada da tool em linguagem natural em vez de executá-la de fato — resultando em relatório não salvo sem nenhum erro visível no pipeline.

**Evidência:** Relatórios ausentes em execuções do pipeline sem mensagem de erro.

**Solução proposta (PR #316):** Substituir o `_persister` por `_persist_review`, um `after_agent_callback` executado em Python puro pelo runtime do ADK logo após o `_analyzer` terminar — zero participação do LLM no passo de escrita.

---

### GAP-02 — Ausência de análise estática determinística *(Severidade: Média)*

O revisor depende **exclusivamente do LLM** para identificar problemas no código. Ferramentas como Ruff e Bandit:

- Executam em milissegundos
- São determinísticas (mesmo input → mesmo output, sempre)
- Não alucinam
- Produzem referências padronizadas a regras (ex: `E501`, `B106`)

Ao não utilizá-las como pré-análise, o agente perde contexto objetivo que poderia enriquecer (e guiar) a análise do LLM, além de depender do LLM para identificar issues que uma ferramenta já resolveria com certeza.

---

### GAP-03 — Conflito `output_schema` + `tools` em `reviewer/agent.py` *(Severidade: Média)*

O `LlmAgent` em `src/agents/reviewer/agent.py` declara simultaneamente `output_schema` e `tools`. O ADK não suporta essa combinação de forma confiável: quando `output_schema` está presente, o agente é instruído a retornar JSON estruturado, o que conflita com o fluxo de chamada de tools.

**Efeito:** Comportamento imprevisível — o agente pode retornar JSON sem chamar as tools, ou chamar as tools sem produzir o schema esperado.

---

## 3. Capacidades Identificadas

Com base nos gaps, foram identificadas as seguintes capacidades a serem implementadas:

### Camada de análise estática (`shared/review/`)

| Capacidade | Ferramenta | Tipo de análise | Saída |
|---|---|---|---|
| `RuffCapability` | Ruff | Linting, estilo, imports não usados | `list[Finding]` |
| `BanditCapability` | Bandit | Segurança (senhas hardcoded, injeção, etc.) | `list[Finding]` |

**Modelo de dado normalizado (`Finding`):**

```python
Finding(
    origem="ruff",           # qual ferramenta
    regra="F401",            # código da regra
    severidade="warning",    # critical | warning | info
    arquivo="app/main.py",   # caminho relativo
    linha=12,                # linha (opcional)
    mensagem="'os' imported but unused",
    sugestao="Remove unused import",  # opcional
)
```

**Protocolo extensível (`ReviewCapability`):**

Qualquer ferramenta futura (Pylint, MyPy, Semgrep, etc.) pode ser adicionada ao `REGISTRY` implementando o protocolo:

```python
class MinhaFerramenta:
    name = "minha-ferramenta"

    def run(self, target_dir: Path) -> list[Finding]:
        ...
```

---

## 4. Ferramentas Avaliadas

### Ruff

| Critério | Avaliação |
|---|---|
| Licença | MIT |
| Performance | Muito alta (implementado em Rust) |
| Formato de saída | JSON nativo via `--output-format json` |
| Já no projeto | Sim, como dependência de dev |
| Cobertura | PEP 8, imports, complexidade, tipo de erros comuns |
| Falsos positivos | Baixos, configuráveis via `pyproject.toml` |

**Decisão:** Promover de `dev` para dependência de runtime — necessário para execução via subprocess no ambiente de produção/Docker.

---

### Bandit

| Critério | Avaliação |
|---|---|
| Licença | Apache 2.0 |
| Performance | Alta |
| Formato de saída | JSON via `--format json` |
| Já no projeto | Não |
| Cobertura | OWASP Top 10, CWE, senhas hardcoded, uso de funções inseguras |
| Severidade nativa | HIGH / MEDIUM / LOW (mapeado para critical/warning/info) |

**Decisão:** Adicionar como dependência de runtime (`bandit>=1.9.4`).

---

### Ferramentas descartadas nesta iteração

| Ferramenta | Motivo do descarte |
|---|---|
| Pylint | Sobrepõe com Ruff; mais lento; configuração mais complexa |
| MyPy | Requer stubs para dependências externas; custo de setup alto |
| Semgrep | Poderoso, mas requer regras customizadas; escopo para iteração futura |

---

## 5. Mudanças Estruturais Propostas

### 5.1 Nova estrutura de arquivos

```
adk/
├── shared/
│   └── review/                        ← NOVO
│       ├── __init__.py                ← reexporta API pública
│       └── capability.py             ← Finding, ReviewCapability, Ruff, Bandit, run_capabilities
├── src/agents/
│   └── workflow_coding_review/
│       └── cr_reviewer.py            ← MODIFICADO (R2: before_agent_callback)
│   └── reviewer/
│       └── agent.py                  ← MODIFICADO (R3: fix GAP-03)
└── tests/unit/
    └── review/                        ← NOVO
        ├── __init__.py
        └── test_capabilities.py
```

### 5.2 Novo fluxo após as mudanças

```
[Coder Workspace]
       │
       ▼
┌──────────────────────────┐
│  before_agent_callback   │  Python puro — roda Ruff + Bandit em paralelo,
│  (static_analysis_hook)  │  injeta findings em ctx.state
└──────────────────────────┘
       │ state["static_findings_block"]
       ▼
┌─────────────────────┐
│   _review_analyzer  │  LlmAgent — recebe findings estáticos no prompt,
│                     │  analisa o código com contexto enriquecido
└─────────────────────┘
       │ (after_agent_callback — via PR #316)
       ▼
 verificacao_revisao.md
```

O `before_agent_callback` roda **antes** do LLM e injeta um bloco como este no prompt do analyzer:

```
# ANÁLISE ESTÁTICA (pré-LLM)
Os seguintes problemas foram identificados por ferramentas determinísticas:

[CRITICAL] bandit/B105 — app/auth.py:14 — Hardcoded password string
[WARNING]  ruff/F401   — app/main.py:3  — 'os' imported but unused
```

O LLM então analisa o código **já ciente** desses issues, focando seu raciocínio nas camadas de arquitetura e corretude onde ele agrega mais valor.

---

## 6. Recomendações de Adoção

| # | Recomendação | Prioridade |
|---|---|---|
| 1 | Implementar a camada `shared/review/` com `Finding`, `ReviewCapability`, `RuffCapability` e `BanditCapability` | Alta |
| 2 | Aprovar e mergear PR #316 (`fix/code/reviewer-remove-persister`) — resolve GAP-01 e é base para R2 | Alta |
| 3 | Integrar `run_capabilities` via `before_agent_callback` no `cr_reviewer._analyzer` | Alta |
| 4 | Corrigir GAP-03 em `reviewer/agent.py` (remover conflito `output_schema` + `tools`) | Média |
| 5 | Adicionar testes de integração com `@pytest.mark.integration` para validar Ruff e Bandit em código real | Média |
| 6 | Avaliar Semgrep para regras customizadas em iteração futura | Baixa |

---

## 7. Detalhamento Técnico das Implementações

Esta seção descreve o código produzido em cada etapa (R1, R2, R3), explicando a sintaxe e a lógica por trás de cada decisão de implementação.

---

### R1 — Camada de capacidades (`shared/review/`)

**Objetivo:** criar uma camada extensível que isola as ferramentas de análise estática do restante do sistema, seguindo o padrão Protocol do Python.

#### 1.1 Modelo de dado: `Finding`

```python
class Finding(BaseModel):
    origem: str
    regra: str
    severidade: Literal["critical", "warning", "info"]
    arquivo: str
    linha: int | None = None
    mensagem: str
    sugestao: str | None = None
```

`Finding` é um modelo Pydantic — o Pydantic valida automaticamente os tipos no momento da criação do objeto. O campo `severidade` usa `Literal`, o que significa que o Python rejeita qualquer valor que não seja exatamente `"critical"`, `"warning"` ou `"info"` — isso garante que nenhuma ferramenta consiga injetar um valor inválido sem que um erro seja lançado imediatamente.

Os campos `linha` e `sugestao` são opcionais (`| None = None`) porque nem toda ferramenta informa linha exata ou sugere correção.

#### 1.2 Protocolo extensível: `ReviewCapability`

```python
class ReviewCapability(Protocol):
    name: str
    def run(self, target_dir: Path) -> list[Finding]: ...
```

`Protocol` é um mecanismo de tipagem estrutural do Python — qualquer classe que possua um atributo `name: str` e um método `run(target_dir)` satisfaz automaticamente o protocolo, **sem precisar herdar ou importar nada**. Isso significa que adicionar uma ferramenta nova no futuro não exige modificar código existente — basta criar a classe com a interface certa e registrá-la no `REGISTRY`.

#### 1.3 Implementação das ferramentas: `RuffCapability` e `BanditCapability`

Ambas seguem o mesmo padrão: executam a ferramenta como subprocesso, leem o JSON da saída padrão e convertem para `list[Finding]`.

```python
class RuffCapability:
    name = "ruff"

    def run(self, target_dir: Path) -> list[Finding]:
        try:
            proc = subprocess.run(
                ["ruff", "check", "--output-format", "json", str(target_dir)],
                capture_output=True,
                text=True,
            )
            if not proc.stdout.strip():
                return []
            items = json.loads(proc.stdout)
        except Exception:
            return []
        ...
```

O bloco `try/except Exception` é intencional e amplo: se o `ruff` não estiver instalado, se o JSON vier malformado, ou se ocorrer qualquer outro problema, a função retorna uma lista vazia em vez de propagar a exceção — isso é o que permite o isolamento de falhas descrito na seção 1.4.

`capture_output=True` direciona `stdout` e `stderr` para atributos do objeto `proc` em vez de imprimir no terminal. `text=True` garante que a saída seja uma string Python em vez de bytes brutos.

Para o Bandit, a lógica é análoga, mas o JSON tem estrutura diferente — os findings ficam dentro de `data["results"]` — e a severidade (`HIGH`/`MEDIUM`/`LOW`) é mapeada explicitamente para o vocabulário do `Finding`:

```python
_SEVERITY_MAP = {"HIGH": "critical", "MEDIUM": "warning", "LOW": "info"}
```

#### 1.4 Execução paralela com isolamento: `run_capabilities`

```python
def run_capabilities(target_dir: Path, registry: list[ReviewCapability] | None = None) -> list[Finding]:
    _registry = registry if registry is not None else REGISTRY
    if not _registry:
        return []
    all_findings: list[Finding] = []
    with ThreadPoolExecutor(max_workers=len(_registry)) as executor:
        futures = {executor.submit(cap.run, target_dir): cap.name for cap in _registry}
        for future in as_completed(futures):
            try:
                all_findings.extend(future.result())
            except Exception:
                pass
    return sorted(all_findings, key=lambda f: _SEVERITY_ORDER[f.severidade])
```

`ThreadPoolExecutor` cria uma pool de threads — cada capacidade roda em paralelo em sua própria thread. `executor.submit(cap.run, target_dir)` agenda a execução e retorna um `Future`, que representa o resultado futuro da chamada.

`as_completed(futures)` itera pelos futures na ordem em que **terminam** (não na ordem em que foram enviados). Para cada future concluído, `future.result()` retorna os findings ou relança a exceção caso a thread tenha falhado — daí o `try/except` que descarta silenciosamente falhas individuais sem afetar as demais ferramentas.

O parâmetro `registry` com valor padrão `None` (em vez de `[]`) é um padrão importante em Python: evitar uma lista mutável como valor padrão de argumento, o que causaria comportamento inesperado se o chamador modificasse a lista.

Ao final, os findings são ordenados por severidade usando `_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}` — critical sempre aparece primeiro.

---

### R2 — Integração no `cr_reviewer` via callbacks

**Objetivo:** conectar a camada de análise estática ao fluxo do agente revisor sem modificar a interface externa do agente.

#### 2.1 Guard de import em tempo de verificação de tipos

```python
if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
else:
    CallbackContext = Any
```

`TYPE_CHECKING` é uma constante do módulo `typing` que vale `True` apenas quando uma ferramenta de análise estática (como o `mypy`) está rodando — nunca em execução real. Isso permite usar `CallbackContext` como anotação de tipo nas assinaturas das funções (para que o editor entenda os atributos do objeto) sem importar o módulo em runtime. A razão: imports de internos do ADK que ainda não estavam estabilizados na versão usada poderiam falhar em tempo de execução. Com esse padrão, qualquer mudança interna do ADK não quebra o módulo ao ser importado.

#### 2.2 Feature flag via variável de ambiente

```python
_STATIC_ANALYSIS_ENABLED = os.environ.get("REVIEWER_STATIC_ANALYSIS", "1") != "0"
```

`os.environ.get("REVIEWER_STATIC_ANALYSIS", "1")` lê a variável de ambiente — se ela não existir, retorna `"1"` como padrão. A comparação `!= "0"` faz com que qualquer valor diferente de `"0"` ative a funcionalidade (padrão: ligada). Isso permite desativar a análise estática em ambientes específicos sem alterar código.

#### 2.3 Template de instrução com placeholders

```python
_ANALYZER_INSTRUCTION_TEMPLATE = (
    _ANALYZER_BASE + "\n\n"
    "# ANÁLISE ESTÁTICA (pré-LLM)\n"
    "...\n\n"
    "__STATIC_FINDINGS__\n\n"
    "# ARQUIVOS A REVISAR\n"
    "__FILES__\n"
)
```

O template usa strings de substituição (`__STATIC_FINDINGS__`, `__CODER_WS__`, `__FILES__`) em vez de f-strings. Isso é intencional: o template é construído **uma vez** no carregamento do módulo, mas os valores reais (findings, lista de arquivos) só existem **no momento em que o agente é invocado**. A substituição acontece dentro do InstructionProvider (veja 2.4).

#### 2.4 InstructionProvider: instrução dinâmica em runtime

```python
def _analyzer_instruction_provider(ctx) -> str:
    static_block = ""
    if hasattr(ctx, "state"):
        static_block = ctx.state.get("static_findings_block", "")
    return (
        _ANALYZER_INSTRUCTION_TEMPLATE
        .replace("__STATIC_FINDINGS__", static_block or "Análise estática não disponível.")
        .replace("__CODER_WS__", _CODER_WS)
        .replace("__FILES__", _discover_coder_files())
    )
```

Quando `instruction` de um `LlmAgent` é um **callable** (função) em vez de uma string, o ADK chama essa função no momento de construir o prompt para o LLM, passando o contexto atual como argumento. Isso é o que o ADK chama de `InstructionProvider`.

A função lê `ctx.state.get("static_findings_block", "")` — esse valor foi injetado pelo `before_agent_callback` (seção 2.5) antes desta função ser chamada, por isso a cadeia funciona: callback injeta → provider lê → LLM recebe no prompt.

O `hasattr(ctx, "state")` protege contra contextos de teste que não têm esse atributo.

#### 2.5 `before_agent_callback`: análise estática antes do LLM

```python
def _inject_static_findings(callback_context: CallbackContext) -> None:
    if not _STATIC_ANALYSIS_ENABLED:
        return None
    coder_path = Path(_CODER_WS)
    if not coder_path.exists():
        callback_context.state["static_findings_block"] = (
            "Workspace do coder não encontrado — análise estática ignorada."
        )
        return None
    findings = run_capabilities(coder_path)
    capped = findings[:_MAX_FINDINGS]
    callback_context.state["static_findings_block"] = _format_findings_block(capped)
    return None
```

`before_agent_callback` é um hook do ADK que é disparado **antes** do agente começar a processar — antes mesmo de qualquer chamada ao LLM. O retorno `None` sinaliza ao ADK para **continuar** o fluxo normal do agente. Se retornasse um `Content`, o ADK usaria aquilo como resposta final e pularia o LLM completamente.

A função armazena os findings em `callback_context.state["static_findings_block"]`. O `state` do `CallbackContext` é o mesmo dicionário que `ctx.state` no `InstructionProvider` — é assim que os dois se comunicam sem precisar de variáveis globais ou argumentos diretos.

`findings[:_MAX_FINDINGS]` limita a 30 findings para não sobrecarregar o prompt do LLM com informações em excesso.

#### 2.6 Conexão final: atribuição dos callbacks

```python
_analyzer.before_agent_callback = _inject_static_findings
_analyzer.after_agent_callback = _persist_review
```

O ADK permite atribuir callbacks diretamente como atributos do `LlmAgent` após sua criação. `before_agent_callback` recebe a função que roda antes do LLM; `after_agent_callback` recebe a função que roda após o agente terminar (implementada no PR #316 para persistir o relatório). Ambas são funções Python comuns — sem LLM envolvido.

---

### R3 — Correção do GAP-00 em `reviewer/agent.py`

**Objetivo:** remover o conflito entre `output_schema` e `tools` no agente revisor original.

#### 3.1 O problema: dois modos incompatíveis

```python
# ANTES — configuração conflitante
agent = create_se_agent(
    ...
    output_schema=schemas.ReviewOutput,   # ← modo "structured output"
    tools=[
        FunctionTool(tool_ler_diff),
        FunctionTool(tool_salvar_relatorio),  # ← modo "tool calling"
    ],
)
```

O ADK opera em dois modos distintos ao configurar um `LlmAgent`:

- **Structured output** (`output_schema`): o LLM é instruído a retornar **exclusivamente** um JSON que corresponde ao schema. O modelo entra em modo de "gramática restrita" — só pode gerar tokens que formem um JSON válido para aquele schema.
- **Tool calling** (`tools`): o LLM pode emitir chamadas de função durante a geração, e o ADK as executa intercalando com a resposta do modelo.

Esses dois modos são mutuamente exclusivos no ADK: com `output_schema` ativo, o modelo não consegue emitir chamadas de tool de forma confiável, pois a gramática restrita do JSON não deixa espaço para o formato de tool-call. O resultado é comportamento imprevisível — o agente ora retorna JSON sem chamar as tools, ora chama as tools e não produz o schema esperado.

#### 3.2 A correção: remover `output_schema`

```python
# DEPOIS — conflito removido
agent = create_se_agent(
    ...
    output_key="review",
    tools=[
        FunctionTool(tool_ler_diff),
        FunctionTool(tool_salvar_relatorio),
    ],
)
```

`output_schema` foi removido. As tools permanecem intactas — são essenciais para o fluxo do agente (ler o diff e salvar o relatório).

`output_key="review"` captura a **última mensagem de texto** do agente no `session.state["review"]`. O LLM ainda é instruído pelo prompt a produzir um JSON com o formato de `ReviewOutput` — mas agora essa instrução vive no texto do prompt (seção `# SAÍDA FINAL`), não como restrição de gramática do ADK. O modelo tem liberdade para chamar as tools e, ao final, produzir o JSON como texto.

A remoção do import `schemas` que ficou sem uso é uma consequência direta:

```python
# ANTES
from . import prompt, schemas

# DEPOIS
from . import prompt
```

---

## 8. Benefícios Esperados

- **Cobertura aumentada:** Issues detectados por ferramentas determinísticas não dependem mais da "atenção" do LLM
- **Análise direcionada:** O LLM recebe contexto objetivo e pode focar em problemas que ferramentas estáticas não conseguem detectar (ex: lógica de negócio, arquitetura)
- **Extensibilidade:** Novas ferramentas entram via `REGISTRY` sem alterar o reviewer
- **Confiabilidade:** Persistência do relatório via Python puro elimina risco de modo narrador
- **Rastreabilidade:** Cada finding tem `origem` e `regra` — o relatório final referencia de onde cada problema veio
