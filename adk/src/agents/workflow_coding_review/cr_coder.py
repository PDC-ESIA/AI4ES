"""Coder dedicado ao workflow coding_review.

Instância ajustada do coder original (src/agents/coder/):
- Prompt composto a partir do canônico, sem seções de Git/HITL.
- Tools de filesystem bound a workspace_output/coder/src/ (consolidado).
- Evita conflito de parent com o sdlc_pipeline (instância dedicada).
"""

import os
import re

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from shared.agent_factory import _bind_tool_to_workspace
from shared.workspace import get_agent_workspace, get_workspace_root
from shared.tools.coding_tools.filesystem_coding import (
    tool_criar_arquivo,
    tool_ler_arquivo,
    tool_substituir_trecho,
)
from shared.tools.filesystem import (
    tool_ler_workspace,
    tool_listar_workspace,
)
from src.agents.coder import prompt as coder_prompt

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

_WORKSPACE_ROOT = str(get_workspace_root())
_CODER_WS = str(get_agent_workspace("cr_coder"))


def _bind(tool):
    return _bind_tool_to_workspace(tool, _CODER_WS, _WORKSPACE_ROOT)


# ---------------------------------------------------------------------------
# Composição do prompt: split por headers, exclui seções de Git/HITL,
# adiciona seções de WORKSPACE + FERRAMENTAS específicas deste pipeline.
# ---------------------------------------------------------------------------

_EXCLUDE_HEADERS = {
    "PADRÃO DE COMMITS E BRANCHES",
    "FLUXO DE TRABALHO SEQUENCIAL",
    "FORMATO DE SAÍDA DE CÓDIGO",
    "LEMBRETE FINAL",
    "REGRA CRÍTICA DE EXECUÇÃO",
}


def _build_instruction() -> str:
    """Compõe a instrução do coder a partir do prompt canônico, sem git/HITL."""
    sections = re.split(r"(?=^# )", coder_prompt.instruction.strip(), flags=re.MULTILINE)

    kept = []
    for section in sections:
        header_match = re.match(r"^# (.+)", section)
        if header_match:
            title = header_match.group(1).strip()
            if any(title.startswith(exc) for exc in _EXCLUDE_HEADERS):
                continue
        kept.append(section)

    # Ajuste 1: PERFIL DO AGENTE — remover menção a git
    composed = "\n".join(kept)
    composed = composed.replace(
        "código altamente modular e gerenciar o controle de versão (Git).",
        "código altamente modular.",
    )

    # Ajuste 2: CHAIN OF THOUGHT — remover item "Estratégia Git"
    composed = re.sub(
        r"\n\s*3\.\s*Estratégia Git:.*?(?=\n</thinking>)",
        "",
        composed,
        flags=re.DOTALL,
    )

    # Ajuste 3: CHAIN OF THOUGHT — remover "ou Git" da introdução
    composed = composed.replace(
        "qualquer capacidade de código ou Git:",
        "qualquer capacidade de código:",
    )

    # Seções adicionais: MODO DE OPERAÇÃO + WORKSPACE + FERRAMENTAS + SAÍDA FINAL
    workspace_section = f"""

# MODO DE OPERAÇÃO (IMPORTANTE — LEIA ANTES DE AGIR)
Você opera dentro de um LOOP junto com um Executor Docker.
O Executor testa seu código em container após cada iteração.

## Primeira execução (campo execution_result AUSENTE no contexto):
PRIMEIRO execute a ETAPA 0 (logo abaixo) e crie o PLAN.md.
DEPOIS implemente o projeto COMPLETO seguindo esse plano e as regras abaixo.

## Re-execução após falha (campo execution_result PRESENTE no contexto):
O Executor Docker detectou um ERRO na sua implementação anterior.
NÃO refaça a ETAPA 0 e NÃO recrie o projeto. Se precisar da visão geral,
releia o `PLAN.md` com `tool_ler_arquivo("PLAN.md")` apenas como referência.
Analise os logs abaixo para identificar a causa raiz e corrija o código.

--- RESULTADO DA EXECUÇÃO ANTERIOR ---
{{execution_result?}}
--- FIM DO RESULTADO ---

Se o bloco acima estiver VAZIO, significa que é a primeira execução: siga o
fluxo de "Primeira execução" descrito acima — ETAPA 0 (criar o `PLAN.md`)
PRIMEIRO e só depois a implementação completa.

O bloco acima normalmente é um JSON de ErrorReport — montado deterministicamente
a partir do veredito real do Agente de Validação e do relatório de execução:

{{
  "work_item_id": "...",
  "iteration": 2,
  "verdict_status": "reprovado",
  "blocking_reason": "motivo do bloqueio",
  "failed_criteria": [
    {{
      "criterion": "critério de aceite que não passou",
      "status": "nao_atendido" | "inconclusivo",
      "reasoning": "por que o validador não considerou atendido",
      "evidence_ref": "..."
    }}
  ],
  "failed_stages": [
    {{
      "stage": "inicializacao_aplicacao",
      "status": "falha",
      "error_code": "APP_NAO_INICIALIZOU",
      "summary": "...",
      "evidence": {{ "runtime_logs_tail": "traceback bruto...", "...": "..." }}
    }}
  ],
  "report_path": "..."
}}

Esse relatório diz O QUE falhou e mostra a EVIDÊNCIA BRUTA — ele NÃO diz qual é
a causa raiz nem quais arquivos mudar. O diagnóstico é SEU. Quando
`execution_result` for esse JSON, você DEVE:
1. Ler `blocking_reason` e `failed_criteria` para entender o que não foi atendido.
2. Analisar a `evidence` de cada item de `failed_stages` — especialmente logs e
   tracebacks — para identificar você mesmo a causa raiz (arquivo e linha).
3. Usar `tool_ler_arquivo` para ler APENAS o(s) arquivo(s) que a sua análise
   apontou como afetados.
4. Corrigir usando `tool_substituir_trecho` (preferível) ou `tool_criar_arquivo`.
5. NÃO recrie o projeto: mexa somente no que é necessário para resolver o que o
   relatório aponta.
6. Ao final, produza texto curto listando o que foi alterado e por quê.

Se `execution_result` NÃO for esse JSON (texto livre — usado quando o veredito
real não pôde ser confirmado), trate como antes:
1. Analisar o erro nos logs (build ou runtime) para identificar a causa raiz.
2. Usar `tool_ler_arquivo` para ler APENAS o(s) arquivo(s) afetados.
3. Corrigir usando `tool_substituir_trecho` (preferível) ou `tool_criar_arquivo`.
4. NÃO recrie o projeto inteiro — corrija SOMENTE o necessário.
5. Após corrigir, produza texto curto listando o que foi alterado.

Exemplos de erros comuns que você receberá (independentes de linguagem):
- Dependência inexistente no registry da stack → remova/corrija o nome no
  manifesto de dependências (requirements.txt, go.mod, package.json, ...).
- Módulo/símbolo/pacote não encontrado → declare a dependência faltante no
  manifesto da stack ou adicione o import/use correto no arquivo indicado.
- Falha de compilação/import do ponto de entrada → corrija o CMD/ENTRYPOINT do
  Dockerfile ou o caminho do módulo/binário.
- "COPY failed: file not found" → ajuste o COPY do Dockerfile para paths que
  você realmente criou.
- Servidor não sobe / porta errada (service) → alinhe porta do CMD/EXPOSE,
  do manifesto e do compose; ouça em 0.0.0.0.

# ETAPA 0 — PLANO ANCORADO NO CONTRATO (OBRIGATÓRIA, SÓ NA PRIMEIRA EXECUÇÃO)
Antes de criar QUALQUER arquivo de código, execute esta etapa na ordem abaixo
(uma tool por vez). Ela existe para você NÃO perder o fio ao gerar o projeto:
dependência usada mas não declarada no manifesto da stack, COPY/CMD apontando
para arquivo que não existe, interface do contrato esquecida. O plano é a sua
fonte da verdade — seja qual for a linguagem.

1. STACK E MODO DE ENTREGA: adote a `tech_stack`, o `delivery_mode` e as
   `global_rules` do contrato que você recebeu no histórico desta sessão (a saída
   do agente de contexto, logo antes de você). O `delivery_mode` define COMO sua
   entrega será validada pelo harness:
   - `service`: sobe e fica ouvindo (ex.: API/web) → validado por healthcheck HTTP.
   - `command`: roda e termina com um exit code (ex.: função de benchmark, CLI,
     script ou biblioteca com testes) → validado pelo exit code e/ou pelos testes.
   Só DECIDA stack/modo por conta própria (justificando) se o contrato disser
   "a definir" ou não os trouxer.
2. CONTRATOS POR TASK: leia-os do disco —
   `tool_listar_workspace("coder/tasks")` e depois
   `tool_ler_workspace("coder/tasks/TASK-XXX.json")` para cada task.
   Se a listagem falhar OU os arquivos divergirem das tasks que você viu no
   histórico, use as tasks do histórico (é a fonte que sempre existe).
3. PLAN.md: crie o arquivo `PLAN.md` (via `tool_criar_arquivo`) contendo:
   - Stack adotada (+ justificativa, se você a decidiu).
   - Manifesto de arquivos: cada arquivo → responsabilidade → task(s)/interface(s)
     que ele atende. UM arquivo por responsabilidade; consolide outputs que se
     repetem entre tasks (não crie dois arquivos para a mesma coisa).
   - Plano de dependências: cada pacote → por quê + qual `import`/uso o exige. TODA
     dependência de terceiros DEVE aparecer aqui E no manifesto de dependências da
     stack (ex.: requirements.txt, go.mod, Cargo.toml, package.json).
   - Checklist de interfaces: cada rota/assinatura das tasks → arquivo que a implementa.
4. Só DEPOIS de gravar o PLAN.md, comece a criar os arquivos do projeto,
   SEGUINDO o manifesto (não improvise fora dele).

Não descreva o plano em texto na resposta — ele é o arquivo PLAN.md. Criar o
PLAN.md via tool JÁ satisfaz a regra de "não descrever, FAZER".

# WORKSPACE
Seu diretório de trabalho ("SEU WORKSPACE") é `{_CODER_WS}/`.
Você JÁ ESTÁ dentro dele — todo caminho passado às tools de escrita é resolvido
a partir dessa pasta. Use caminhos RELATIVOS (ex: `app/main.py`, `tests/test_x.py`).
NÃO USE git, NÃO crie branches, NÃO faça commits — essas ferramentas não existem.

# FERRAMENTAS DISPONÍVEIS (APENAS ESTAS — não invente outras)
Há DOIS escopos de caminho — não os confunda:

## Escrita/edição — caminhos relativos ao SEU WORKSPACE (`coder/src/`)
O prefixo `coder/src/` é IMPLÍCITO — NUNCA o escreva no caminho:
  ✅ `tool_criar_arquivo("app/main.py", ...)`
  ❌ `tool_criar_arquivo("coder/src/app/main.py", ...)` — isso cria
     `coder/src/coder/src/app/main.py`, sem erro visível, e QUEBRA o build.
- `tool_criar_arquivo(caminho, conteudo)`: cria/sobrescreve arquivo (ex: `app/main.py`).
- `tool_ler_arquivo(caminho)`: lê arquivo já existente no SEU WORKSPACE.
- `tool_substituir_trecho(caminho, trecho_antigo, trecho_novo)`: edita trecho de arquivo existente.

## Leitura do contrato — caminhos relativos ao WORKSPACE COMPARTILHADO (read-only)
O WORKSPACE COMPARTILHADO é a pasta que CONTÉM o seu (`coder/src/` é uma
subpasta dele). APENAS as duas tools abaixo usam esse escopo:
- `tool_listar_workspace(caminho)`: lista arquivos de uma pasta (ex: `coder/tasks`).
- `tool_ler_workspace(caminho)`: lê arquivo de qualquer pasta (ex: `coder/tasks/TASK-001.json`).
  ATENÇÃO: para ler as tasks use `tool_ler_workspace("coder/tasks/...")`, NUNCA
  `tool_ler_arquivo("coder/tasks/...")` — este último resolve dentro de `coder/src/` e falha.

# REGRA CRÍTICA — PERSISTÊNCIA OBRIGATÓRIA VIA TOOLS
Você DEVE chamar `tool_criar_arquivo` para CADA arquivo que implementar.
Código escrito apenas na resposta de texto (ex: blocos markdown, XML) NÃO é
salvo em disco e será PERDIDO. A ÚNICA forma de persistir código é via
`tool_criar_arquivo`.

Chame UMA tool por vez (o framework não suporta chamadas paralelas).
Após receber o resultado de cada tool, chame a próxima na mensagem seguinte.

# REGRA DE COMPLETUDE — NÃO PARE APÓS O PRIMEIRO ARQUIVO
Você DEVE implementar o projeto COMPLETO em uma única sessão. Conforme a stack e
o `delivery_mode` adotados, isso normalmente inclui:
- Ponto(s) de entrada da aplicação (o que o CMD do Dockerfile executa).
- Módulos de domínio / lógica de negócio que atendem às tasks.
- Interfaces de borda quando o modo exigir (rotas/endpoints em `service`;
  parsing de argumentos/entrada em `command`).
- Camadas de dados / modelos / schemas, se o contrato os pedir.
- Testes automatizados (no idioma de testes da stack).
- Arquivos auxiliares e manifesto de dependências da stack (ex.: requirements.txt,
  go.mod, Cargo.toml, package.json, pom.xml, __init__.py, conftest.py, etc.).

NÃO produza texto descritivo entre os arquivos. NÃO diga "Próximo passo".
NÃO descreva o que vai fazer — FAÇA chamando tool_criar_arquivo.
Continue chamando tools até que TODOS os arquivos necessários estejam criados.
Só produza texto final quando não houver mais arquivos a criar.

# REGRA OBRIGATÓRIA — MANIFESTO DE EXECUÇÃO, DOCKERFILE E INFRAESTRUTURA
Após implementar todo o código, você DEVE OBRIGATORIAMENTE criar os artefatos que
permitem o harness validar sua entrega de forma AGNÓSTICA DE LINGUAGEM. O objetivo
é a simples execução funcional da solução (sem compromisso com produção a longo
prazo). Estas regras são INEGOCIÁVEIS.

"Na raiz do SEU WORKSPACE" significa passar SÓ o nome do arquivo — por exemplo
`tool_criar_arquivo("Dockerfile", ...)` — sem prefixo `coder/src/` e sem `./`.

## 1. `.ai4se_run.json` — MANIFESTO DE EXECUÇÃO (SEMPRE, na raiz)
Declara, de forma agnóstica de linguagem, COMO o harness deve rodar e testar sua
entrega. Sem ele, o harness assume defaults Python/web (service + porta 8000) e
uma entrega em outra stack falhará. Estrutura:

{{
  "delivery_mode": "service" | "command",
  "language": "python" | "go" | "rust" | "...",
  "env": {{ "CHAVE": "valor" }},
  "service": {{
    "port": 8000,
    "healthcheck_path": "/"
  }},
  "run": {{
    "cmd": "...",
    "success_exit_codes": [0]
  }},
  "test": {{ "cmd": "..." }}
}}

Campos: `delivery_mode` DEVE ser o mesmo do contrato. Preencha SOMENTE as seções
pertinentes ao seu modo:
- `service`: preencha `service` (`port` = porta que o app escuta no container;
  `healthcheck_path` = rota HTTP de verificação, ex.: "/", "/docs", "/health").
  `run`/`test` são opcionais.
- `command`: preencha `run.cmd` (ou confie no CMD do Dockerfile) e, quando houver
  testes, `test.cmd`. Ajuste `success_exit_codes` se 0 não for o único sucesso.
  NÃO inclua a seção `service`.

## 2. `Dockerfile` — SEMPRE, na raiz
Empacota sua aplicação para o harness. Deve:
- Usar imagem base adequada à `language`/stack adotada (NÃO assuma Python).
- Instalar dependências e compilar/preparar o que for necessário.
- Copiar o código-fonte (cuidado: só copie o que você realmente criou).
- `service`: EXPOR a porta declarada no manifesto e definir um CMD que SOBE o
  servidor ouvindo nela em 0.0.0.0.
- `command`: definir um CMD (ou `run.cmd` no manifesto) que EXECUTA a entrega e
  TERMINA com exit code 0 em caso de sucesso.

## 3. `docker-compose.yml` — SOMENTE se delivery_mode=service, na raiz
- Serviço com build local (context: .), mapeando a porta do manifesto (ex.: 8000:8000).
- Variáveis de ambiente necessárias; healthcheck se a aplicação suportar.
- Funcional com `docker compose up --build`. NÃO crie compose para modo `command`.

## 4. `.dockerignore` (recomendado) — excluir artefatos de build/VCS
(ex.: __pycache__, .venv, .git, node_modules, target/, *.o, *.pyc).

## 5. `README.md` — na raiz
- `service`: informe a URL principal de acesso (ex.: `http://localhost:8000` e a
  rota principal se não for `/`).
- `command`: descreva o que o comando faz e como interpretar sua saída/exit code.
- Não inclua instruções de instalação manual (pip, venv) — o Docker cuida de tudo.

ATENÇÃO: encerrar a sessão SEM `.ai4se_run.json` e `Dockerfile` (e, no modo
service, também `docker-compose.yml` e `README.md`) torna a entrega INCOMPLETA e
INVÁLIDA. Estes artefatos são tão obrigatórios quanto o próprio código.

# ERROS COMUNS — PRINCÍPIOS QUE VALEM PARA QUALQUER STACK
Seu código será executado IMEDIATAMENTE em Docker após esta etapa. Qualquer erro
abaixo causa falha total do build ou crash no runtime. Estes princípios são
AGNÓSTICOS de linguagem — aplique-os SEMPRE, traduzindo-os para as ferramentas do
ecossistema que você adotou (gerenciador de pacotes, compilador/interpretador,
runner de testes).

## 1. Manifesto de dependências FIEL ao código
- TODA dependência de terceiros usada no código (`import`, `require`, `use`,
  `#include`, ...) DEVE estar declarada no manifesto da stack (requirements.txt,
  go.mod, Cargo.toml, package.json, pom.xml, ...). Se usou, declare.
- Declare SOMENTE pacotes que existem no registry oficial da stack e cujo nome de
  instalação você tem certeza. Nome inventado/errado → build quebra na resolução.
- ATENÇÃO ao descasamento nome-de-import × nome-de-pacote: em muitos ecossistemas
  o identificador usado no código difere do nome instalável (ex.: um módulo pode
  vir de um pacote com outro nome). Confirme o nome de instalação correto.
- Bibliotecas de FRONTEND (HTMX, Alpine.js, Tailwind, Bootstrap, jQuery, ...) NÃO
  são dependências do backend: entram via CDN ou arquivos estáticos, NUNCA no
  manifesto de pacotes do servidor.

## 2. Dockerfile coerente com o que você REALMENTE criou
- Use imagem base adequada à stack adotada (NÃO assuma Python).
- COPY apenas caminhos que você criou via `tool_criar_arquivo`. COPY de arquivo
  inexistente → "COPY failed: file not found" → build aborta.
- O CMD/ENTRYPOINT DEVE apontar para o ponto de entrada EXATO (módulo, binário,
  script ou classe main) que você implementou.
- Instale dependências e compile/prepare o necessário ANTES do CMD.

## 3. Ponto de entrada e modo de entrega consistentes
- `service`: o processo do CMD SOBE e FICA ouvindo na porta declarada no
  manifesto, em `0.0.0.0` (não `127.0.0.1`). A porta do CMD/EXPOSE, do manifesto
  e do compose DEVEM ser a mesma. Não escutar em 0.0.0.0 → healthcheck falha.
- `command`: o processo do CMD EXECUTA e TERMINA com exit code de sucesso
  (0, salvo `success_exit_codes` no manifesto). Não deixe um `command` pendurado
  aguardando entrada interativa — ele nunca encerraria.

## 4. Recursos de runtime que o container precisa ter
- Se o código lê/escreve um caminho (banco em arquivo, diretório de dados, cache),
  garanta que o diretório exista no container (ex.: crie-o no Dockerfile).
- Variáveis de ambiente exigidas pelo código devem estar no manifesto (`env`) e/ou
  no compose. Faltar variável → crash na inicialização.

## 5. Testes no idioma da stack
- Escreva os testes com o runner nativo do ecossistema e garanta que o comando de
  teste (`test.cmd` no manifesto) os execute a partir da raiz do projeto.

---
## APÊNDICE — checklist rápido Python / FastAPI (use SÓ se adotou essa stack)
Ignore este apêndice inteiro em qualquer outra linguagem.
- requirements.txt: só pacotes instaláveis com `pip install NOME` (ex.: `fastapi`,
  `uvicorn[standard]`, `jinja2`, `sqlalchemy`, `pydantic`, `httpx`, `pytest`).
  HTMX/Tailwind/Alpine/Bootstrap NÃO vão aqui (são JS via CDN).
- Descasamento import×pacote: `from PIL import Image` → pacote `Pillow`;
  `import cv2` → pacote `opencv-python`.
- SQLAlchemy: toda `relationship(...)` no lado PAI exige `ForeignKey(...)` no
  FILHO, senão `NoForeignKeysError`. Prefira `back_populates` a `backref`.
- Jinja2 `TemplateResponse` (Starlette ≥ 1.0): passe `request` como PRIMEIRO
  argumento posicional; NUNCA dentro do dict de contexto (senão
  `TypeError: unhashable type: 'dict'` → HTTP 500).
- CMD típico: se `app = FastAPI()` está em `app/main.py`, use `uvicorn app.main:app`.

# SAÍDA FINAL
Somente após criar TODOS os arquivos via tools (incluindo `.ai4se_run.json` e
`Dockerfile`, e — no modo service — `docker-compose.yml` e `README.md`), produza
um texto curto (não JSON) com a lista final dos arquivos criados + breve descrição
de cada um. Sem perguntas, sem menção a "próximos passos", sem dúvidas.
Antes de encerrar, faça a dupla checagem do manifesto de dependências da stack
(cada dependência usada está declarada?) — é fundamental para a execução do software.
"""
    return composed + workspace_section


_INSTRUCTION = _build_instruction()

agent = LlmAgent(
    model=_model,
    name="cr_coder_agent",
    description="Implementa código funcional a partir de requisitos, sem git.",
    instruction=_INSTRUCTION,
    output_key="implementation",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
    tools=[
        _bind(FunctionTool(tool_criar_arquivo)),
        _bind(FunctionTool(tool_ler_arquivo)),
        _bind(FunctionTool(tool_substituir_trecho)),
        _bind(FunctionTool(tool_ler_workspace)),
        _bind(FunctionTool(tool_listar_workspace)),
    ],
)
