# P1: Evolucao Core - Action Planner & Autonomia

## Objetivo

Forcar comportamento preditivo do `qa_agent` e reduzir intervencoes manuais no
fluxo de geracao, execucao e correcao de testes automatizados.

## Checklist das subtasks

- [x] Subtask 1: Atualizar `qa_prompt.py` para obrigar uso do `action_planner`
  antes da execucao.
- [x] Subtask 2: Otimizar integracao das tools para minimizar bloqueios quando
  a acao for obvia.
- [x] Subtask 3: Refinar handoff inter-agentes para evitar perda de contexto e
  documentar as otimizacoes no codigo.

## Relacao com a feature Action Planner

O `action_planner` foi desenvolvido em uma task anterior e possui documentacao
propria de evidencias em:

- `agents/roles/qa_agent/docs/action_planner_evidencias.md`

Este documento de P1 registra apenas as mudancas feitas para integrar esse
planner ao fluxo core do `qa_agent`, reforcar autonomia e melhorar handoffs
entre agentes.

## Subtask 1 - Action Planner antes da execucao

### Mudanca aplicada

Arquivo alterado:

- `agents/roles/qa_agent/qa_prompt.py`

Foi adicionada a secao `ACTION PLANNER`, exigindo que o agente use o
subagente `action_planner` antes de gerar, executar ou corrigir testes.

O fluxo de execucao tambem passou a iniciar com:

1. acionar o `action_planner`;
2. validar o plano de acao;
3. seguir somente a partir do plano produzido.

### Testes

#### Teste 1.1

**Teste:** enviar um requisito simples de login e verificar se o fluxo comeca
pelo `action_planner`.

```text
Gere testes pytest para este requisito:

RF-001: O sistema deve validar login.
- Se usuario e senha estiverem corretos, o login deve retornar sucesso.
- Se usuario ou senha estiverem incorretos, deve retornar erro de autenticacao.
- Usuario vazio ou senha vazia devem ser rejeitados.
```

**Evidencia esperada:** o `action_planner` deve ser chamado antes de qualquer
outra tool ou subagente.

**Evidencia retornada:** o `action_planner` foi chamado antes de qualquer outra
tool ou subagente.

#### Teste 1.2

**Teste:** gerar testes pytest para cadastro de usuario com nome, email e senha
validos, recusando email duplicado e senha com menos de 8 caracteres.

```text
Gere testes pytest para este requisito:

RF-002: O sistema deve permitir cadastro de usuario.
- Nome, email e senha validos devem criar o usuario com sucesso.
- Email duplicado deve ser recusado.
- Senha com menos de 8 caracteres deve ser rejeitada.
- O teste deve cobrir sucesso, duplicidade e senha invalida.
```

**Evidencia esperada:** o `action_planner` deve ser chamado antes de qualquer
outra tool ou subagente.

**Evidencia retornada:** o `action_planner` foi chamado antes de qualquer outra
tool ou subagente.

#### Teste 1.3

**Teste:** criar testes automatizados para uma API de recuperacao de senha com
email existente, email inexistente e token expirado.

```text
Gere testes pytest para este requisito:

RF-003: O sistema deve permitir recuperacao de senha.
- Quando o email existir, o sistema deve gerar um token de recuperacao.
- Quando o email nao existir, a resposta deve ser segura e nao deve vazar se o
  email esta cadastrado.
- Token expirado deve impedir a redefinicao de senha.
```

**Evidencia esperada:** o `action_planner` deve ser chamado antes de qualquer
outra tool ou subagente.

**Evidencia retornada:** o `action_planner` foi chamado antes de qualquer outra
tool ou subagente.

#### Teste 1.4

**Teste:** gerar testes pytest para alteracao de senha quando a senha atual esta
correta, quando esta incorreta e quando a nova senha nao atende a politica
minima.

```text
Gere testes pytest para este requisito:

RF-004: O usuario autenticado deve conseguir alterar a propria senha.
- Se a senha atual estiver correta e a nova senha atender a politica minima, a
  alteracao deve ser concluida.
- Se a senha atual estiver incorreta, a alteracao deve ser negada.
- Se a nova senha nao atender a politica minima, a alteracao deve ser rejeitada.
```

**Evidencia esperada:** o `action_planner` deve ser chamado antes de qualquer
outra tool ou subagente.

**Evidencia retornada:** o `action_planner` foi chamado antes de qualquer outra
tool ou subagente.

#### Teste 1.5

**Teste:** planejar e gerar testes para consulta de pedidos, cobrindo usuario
autenticado, usuario sem autenticacao e pedido inexistente.

```text
Gere testes pytest para este requisito:

RF-005: O sistema deve permitir consulta de pedidos.
- Usuario autenticado deve visualizar apenas os seus pedidos.
- Usuario sem autenticacao deve receber erro 401.
- Consulta de pedido inexistente deve retornar 404.
- O teste deve verificar que pedidos de outros usuarios nao sao expostos.
```

**Evidencia esperada:** o `action_planner` deve ser chamado antes de qualquer
outra tool ou subagente.

**Evidencia retornada:** o `action_planner` foi chamado antes de qualquer outra
tool ou subagente.

#### Teste 1.6

**Teste:** gerar testes pytest para carrinho de compras, cobrindo adicionar item
valido, remover item existente, impedir quantidade negativa e recalcular total.

```text
Gere testes pytest para este requisito:

RF-006: O sistema deve manter um carrinho de compras.
- Adicionar um item valido deve incluir o produto no carrinho.
- Remover um item existente deve remove-lo do carrinho.
- Quantidade negativa deve ser rejeitada.
- O total do carrinho deve ser recalculado apos cada alteracao.
```

**Evidencia esperada:** o `action_planner` deve ser chamado antes de qualquer
outra tool ou subagente.

**Evidencia retornada:** o `action_planner` foi chamado antes de qualquer outra
tool ou subagente.

#### Teste 1.7

**Teste:** criar testes para formulario de endereco com CEP obrigatorio, numero
obrigatorio, complemento opcional e UF limitada a siglas validas.

```text
Gere testes pytest para este requisito:

RF-007: O sistema deve validar formulario de endereco.
- CEP e numero sao obrigatorios.
- Complemento e opcional.
- UF deve aceitar apenas siglas validas de estados brasileiros.
- O teste deve cobrir endereco valido, campos obrigatorios ausentes e UF
  invalida.
```

**Evidencia esperada:** o `action_planner` deve ser chamado antes de qualquer
outra tool ou subagente.

**Evidencia retornada:** o `action_planner` foi chamado antes de qualquer outra
tool ou subagente.

#### Teste 1.8

**Teste:** gerar testes pytest para upload de arquivo aceitando PDF ate 5MB e
rejeitando arquivo acima do limite ou extensao nao permitida.

```text
Gere testes pytest para este requisito:

RF-008: O sistema deve validar upload de documentos.
- Arquivos PDF com ate 5MB devem ser aceitos.
- Arquivos acima de 5MB devem ser rejeitados.
- Extensoes diferentes de PDF devem ser rejeitadas.
- O teste deve cobrir sucesso, limite excedido e extensao invalida.
```

**Evidencia esperada:** o `action_planner` deve ser chamado antes de qualquer
outra tool ou subagente.

**Evidencia retornada:** o `action_planner` foi chamado antes de qualquer outra
tool ou subagente.

#### Teste 1.9

**Teste:** gerar testes para filtro de busca de produtos por nome, categoria e
faixa de preco, incluindo busca sem resultados.

```text
Gere testes pytest para este requisito:

RF-009: O sistema deve permitir busca de produtos com filtros.
- Deve ser possivel filtrar por nome.
- Deve ser possivel filtrar por categoria.
- Deve ser possivel filtrar por faixa de preco.
- Quando nenhum produto corresponder aos filtros, o retorno deve ser uma lista
  vazia controlada.
```

**Evidencia esperada:** o `action_planner` deve ser chamado antes de qualquer
outra tool ou subagente.

**Evidencia retornada:** o `action_planner` foi chamado antes de qualquer outra
tool ou subagente.

#### Teste 1.10

**Teste:** criar testes automatizados para logout, cobrindo usuario autenticado,
chamada repetida idempotente e usuario sem sessao.

```text
Gere testes pytest para este requisito:

RF-010: O sistema deve permitir logout.
- Usuario autenticado deve encerrar a sessao com sucesso.
- Chamada repetida de logout deve ser idempotente.
- Usuario sem sessao ativa deve receber resposta controlada, sem erro interno.
```

**Evidencia esperada:** o `action_planner` deve ser chamado antes de qualquer
outra tool ou subagente.

**Evidencia retornada:** o `action_planner` foi chamado antes de qualquer outra
tool ou subagente.

## Subtask 2 - Less Prompt, More Action

### Mudanca aplicada

Arquivos alterados:

- `agents/roles/qa_agent/subagents/action_planner/prompt.py`
- `agents/roles/qa_agent/tools/planner_tools.py`

O `action_planner` passou a declarar uma decisao explicita de autonomia:

- `autonomy_decision.mode="autonomous"` para ações obvias, locais, reversiveis
  e de baixo risco;
- `autonomy_decision.mode="hitl_required"` para acoes ambiguas, destrutivas,
  externas ou que precisem de decisao humana.

O validador `plan_validator` passou a aceitar e validar:

- `risk_assessment`;
- `autonomy_decision`;
- `lifecycle.execution_allowed`;
- compatibilidade entre `autonomy_decision.mode` e `hitl_checkpoint.required`.

Para manter compatibilidade com planos antigos, esses campos possuem fallback
conservador para HITL quando estiverem ausentes.

### Testes

#### Teste 2.1

**Teste:** executar uma validacao local de plano autonomo e verificar se o
checkpoint HITL nao bloqueia a execucao.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator, create_hitl_checkpoint

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {
        "nivel": "baixo",
        "motivos": ["gera e executa testes locais"],
        "acoes_reversiveis": True,
        "efeito_externo": False,
    },
    "autonomy_decision": {
        "mode": "autonomous",
        "reason": "acao obvia e reversivel",
        "less_prompt_more_action": True,
    },
    "lifecycle": {
        "status": "planejado_para_execucao",
        "execution_allowed": True,
        "next_step": "executar_plano",
    },
    "hitl_checkpoint": {
        "required": False,
        "checkpoint_id": None,
        "pause_reason": None,
        "approval_question": None,
        "allowed_decisions": [],
    },
    "analise_inicial": {
        "linguagem_suspeita": "python",
        "funcao_suspeita_do_codigo": None,
        "nivel_de_confianca": 0.8,
    },
    "analise_progressiva": [
        {
            "observacao": "ha requisito testavel",
            "hipotese": "gerar pytest",
            "validacao_planejada": "executar suite",
        }
    ],
    "criterios_verificaveis": ["login valido passa"],
    "objetivo_qa": "gerar e executar teste",
    "estrategia": ["gerar teste", "executar pytest"],
    "checklist_inicial": [
        {"id": "CHK-01", "descricao": "testes gerados", "status": "pendente"}
    ],
    "handoff_context": {
        "objetivo": "testar login",
        "contexto_compacto": "RF de login",
        "artefatos_relevantes": [],
        "decisoes_tomadas": ["execucao autonoma"],
        "riscos_e_duvidas": [],
        "evidencias_necessarias": ["resultado pytest"],
    },
    "relatorio_conformidade_esperado": {
        "comparar_planejado_vs_executado": True,
        "incluir_evidencias": True,
        "incluir_divergencias": True,
        "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"],
    },
    "doubt": None,
}

payload = json.dumps(plan, ensure_ascii=False)
print(plan_validator(payload))
print(create_hitl_checkpoint(payload))
'@ | uv run python -
```

**Evidencia esperada:** `plan_validator` deve retornar `valid=True`, e
`create_hitl_checkpoint` deve retornar `status: not_required_autonomous_execution`
com `execution_allowed: True`.

**Evidencia retornada:**
{'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['qa_runner_agent']}
{'status': 'not_required_autonomous_execution', 'checkpoint_id': None, 'approval_question': None, 'pause_reason': None, 'allowed_decisions': [], 'execution_allowed': True, 'autonomy_mode': 'autonomous', 'message': 'Checkpoint HITL nao criado. O plano foi validado para execucao autonoma de baixo risco.'}

Isso confirma que um plano obvio e de baixo risco nao fica bloqueado por HITL.

#### Teste 2.2

**Teste:** validar um plano autonomo para gerar e executar pytest de login
local, sem alterar arquivos fora da suite de testes.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator, create_hitl_checkpoint

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {"nivel": "baixo", "motivos": ["gera e executa testes locais de login"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "autonomous", "reason": "acao local, obvia e reversivel", "less_prompt_more_action": True},
    "lifecycle": {"status": "planejado_para_execucao", "execution_allowed": True, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": False, "checkpoint_id": None, "pause_reason": None, "approval_question": None, "allowed_decisions": []},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": None, "nivel_de_confianca": 0.85},
    "analise_progressiva": [{"observacao": "requisito de login testavel", "hipotese": "gerar e executar pytest", "validacao_planejada": "validar suite de login"}],
    "criterios_verificaveis": ["login valido", "login invalido", "campos vazios"],
    "objetivo_qa": "Gerar e executar testes locais de login",
    "estrategia": ["gerar testes pytest", "executar pytest local"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "suite de login validada", "status": "pendente"}],
    "handoff_context": {"objetivo": "testar login", "contexto_compacto": "login local sem alterar arquivos fora da suite", "artefatos_relevantes": ["RF-login"], "decisoes_tomadas": ["execucao autonoma"], "riscos_e_duvidas": [], "evidencias_necessarias": ["resultado pytest"]},
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

payload = json.dumps(plan, ensure_ascii=False)
print(plan_validator(payload))
print(create_hitl_checkpoint(payload))
'@ | uv run python -
```

**Evidencia esperada:** `plan_validator` deve retornar `valid=True`;
`create_hitl_checkpoint` deve retornar `status: not_required_autonomous_execution`
e `execution_allowed: True`.

**Evidencia retornada:**
{'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['qa_runner_agent']}
{'status': 'not_required_autonomous_execution', 'checkpoint_id': None, 'approval_question': None, 'pause_reason': None, 'allowed_decisions': [], 'execution_allowed': True, 'autonomy_mode': 'autonomous', 'message': 'Checkpoint HITL nao criado. O plano foi validado para execucao autonoma de baixo risco.'}

Funcionamento correto

#### Teste 2.3

**Teste:** validar um plano autonomo para criar testes de cadastro de usuario em
ambiente local, com acoes reversiveis e sem efeito externo.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator, create_hitl_checkpoint

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {"nivel": "baixo", "motivos": ["gera teste local para cadastro"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "autonomous", "reason": "cadastro sera testado com dados ficticios locais", "less_prompt_more_action": True},
    "lifecycle": {"status": "planejado_para_execucao", "execution_allowed": True, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": False, "checkpoint_id": None, "pause_reason": None, "approval_question": None, "allowed_decisions": []},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": None, "nivel_de_confianca": 0.8},
    "analise_progressiva": [{"observacao": "cadastro possui criterios objetivos", "hipotese": "validar sucesso e rejeicoes", "validacao_planejada": "executar pytest"}],
    "criterios_verificaveis": ["cadastro valido", "email duplicado", "senha curta"],
    "objetivo_qa": "Validar cadastro de usuario",
    "estrategia": ["gerar teste", "executar suite local"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "criterios de cadastro cobertos", "status": "pendente"}],
    "handoff_context": {"objetivo": "testar cadastro", "contexto_compacto": "cadastro com nome, email e senha", "artefatos_relevantes": ["RF-cadastro"], "decisoes_tomadas": ["usar dados ficticios"], "riscos_e_duvidas": [], "evidencias_necessarias": ["resultado pytest"]},
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

payload = json.dumps(plan, ensure_ascii=False)
print(plan_validator(payload))
print(create_hitl_checkpoint(payload))
'@ | uv run python -
```

**Evidencia esperada:** o plano deve ser aceito como valido, com
`autonomy_decision.mode="autonomous"` compativel com
`hitl_checkpoint.required=False`.

**Evidencia retornada:**
{'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['qa_runner_agent']}
{'status': 'not_required_autonomous_execution', 'checkpoint_id': None, 'approval_question': None, 'pause_reason': None, 'allowed_decisions': [], 'execution_allowed': True, 'autonomy_mode': 'autonomous', 'message': 'Checkpoint HITL nao criado. O plano foi validado para execucao autonoma de baixo risco.'}

Funcionamento correto

#### Teste 2.4

**Teste:** validar um plano para executar apenas a suite pytest ja existente de
autenticacao, sem criar ou remover arquivos.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator, create_hitl_checkpoint

plan = {
    "tipo_entrada": "codigo",
    "modo": "codigo",
    "tools": ["executar_pytest_tool"],
    "risk_assessment": {"nivel": "baixo", "motivos": ["executa suite ja existente"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "autonomous", "reason": "apenas execucao local de pytest", "less_prompt_more_action": True},
    "lifecycle": {"status": "planejado_para_execucao", "execution_allowed": True, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": False, "checkpoint_id": None, "pause_reason": None, "approval_question": None, "allowed_decisions": []},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": "autenticacao", "nivel_de_confianca": 0.9},
    "analise_progressiva": [{"observacao": "arquivo pytest ja existe", "hipotese": "executar sem alteracao", "validacao_planejada": "observar retorno pytest"}],
    "criterios_verificaveis": ["suite de autenticacao executa"],
    "objetivo_qa": "Executar suite pytest de autenticacao existente",
    "estrategia": ["executar pytest no arquivo informado"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "pytest executado", "status": "pendente"}],
    "handoff_context": {"objetivo": "executar testes existentes", "contexto_compacto": "sem criar ou remover arquivos", "artefatos_relevantes": ["tests/test_auth.py"], "decisoes_tomadas": ["usar executar_pytest_tool"], "riscos_e_duvidas": [], "evidencias_necessarias": ["saida pytest"]},
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

payload = json.dumps(plan, ensure_ascii=False)
print(plan_validator(payload))
print(create_hitl_checkpoint(payload))
'@ | uv run python -
```

**Evidencia esperada:** o validador deve aceitar a execucao autonoma por ser uma
acao local, obvia, reversivel e de baixo risco.

**Evidencia retornada:** 
{'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['executar_pytest_tool']}
{'status': 'not_required_autonomous_execution', 'checkpoint_id': None, 'approval_question': None, 'pause_reason': None, 'allowed_decisions': [], 'execution_allowed': True, 'autonomy_mode': 'autonomous', 'message': 'Checkpoint HITL nao criado. O plano foi validado para execucao autonoma de baixo risco.'}

Funcionamento correto

#### Teste 2.5

**Teste:** validar um plano autonomo para gerar testes de recuperacao de senha
usando dados ficticios e sem envio real de email.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator, create_hitl_checkpoint

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {"nivel": "baixo", "motivos": ["usa dados ficticios e nao envia email real"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "autonomous", "reason": "teste local sem efeito externo", "less_prompt_more_action": True},
    "lifecycle": {"status": "planejado_para_execucao", "execution_allowed": True, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": False, "checkpoint_id": None, "pause_reason": None, "approval_question": None, "allowed_decisions": []},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": None, "nivel_de_confianca": 0.82},
    "analise_progressiva": [{"observacao": "recuperacao de senha pode ser testada com mocks", "hipotese": "nao ha envio real", "validacao_planejada": "executar pytest com dados fake"}],
    "criterios_verificaveis": ["email existente", "email inexistente", "token expirado"],
    "objetivo_qa": "Gerar testes de recuperacao de senha sem efeitos externos",
    "estrategia": ["mockar envio", "validar respostas", "executar pytest"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "fluxos de recuperacao validados", "status": "pendente"}],
    "handoff_context": {"objetivo": "testar recuperacao de senha", "contexto_compacto": "sem envio real de email", "artefatos_relevantes": ["RF-recuperacao-senha"], "decisoes_tomadas": ["usar mocks"], "riscos_e_duvidas": [], "evidencias_necessarias": ["resultado pytest"]},
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

payload = json.dumps(plan, ensure_ascii=False)
print(plan_validator(payload))
print(create_hitl_checkpoint(payload))
'@ | uv run python -
```

**Evidencia esperada:** o plano deve ser valido e nao exigir HITL, pois o efeito
externo deve estar marcado como `False`.

**Evidencia retornada:**
{'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['qa_runner_agent']}
{'status': 'not_required_autonomous_execution', 'checkpoint_id': None, 'approval_question': None, 'pause_reason': None, 'allowed_decisions': [], 'execution_allowed': True, 'autonomy_mode': 'autonomous', 'message': 'Checkpoint HITL nao criado. O plano foi validado para execucao autonoma de baixo risco.'}

#### Teste 2.6

**Teste:** validar o caso inverso da autonomia: quando o plano tem ambiguidade
real ou risco alto, o agente deve exigir intervencao humana antes da execucao.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator, create_hitl_checkpoint

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["receber_requisitos"],
    "risk_assessment": {
        "nivel": "alto",
        "motivos": ["requisito ambiguo pode alterar o escopo dos testes"],
        "acoes_reversiveis": True,
        "efeito_externo": False,
    },
    "autonomy_decision": {
        "mode": "hitl_required",
        "reason": "ha ambiguidade real antes da execucao",
        "less_prompt_more_action": False,
    },
    "lifecycle": {
        "status": "aguardando_validacao_humana",
        "execution_allowed": False,
        "next_step": "executar_plano",
    },
    "hitl_checkpoint": {
        "required": True,
        "checkpoint_id": "HITL-CHK-001",
        "pause_reason": "ambiguidade no requisito antes da geracao dos testes",
        "approval_question": "Aprova executar o plano mesmo com a ambiguidade identificada?",
        "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"],
    },
    "analise_inicial": {
        "linguagem_suspeita": "desconhecida",
        "funcao_suspeita_do_codigo": None,
        "nivel_de_confianca": 0.4,
    },
    "analise_progressiva": [
        {
            "observacao": "o requisito usa criterio subjetivo sem regra objetiva",
            "hipotese": "a geracao automatica pode cobrir o comportamento errado",
            "validacao_planejada": "pedir aprovacao humana antes da execucao",
        }
    ],
    "criterios_verificaveis": ["criterio ainda precisa de aprovacao"],
    "objetivo_qa": "Validar requisito ambiguo antes de gerar testes",
    "estrategia": ["pausar para HITL", "executar somente apos aprovacao"],
    "checklist_inicial": [
        {"id": "CHK-01", "descricao": "aprovacao humana registrada", "status": "pendente"}
    ],
    "relatorio_conformidade_esperado": {
        "comparar_planejado_vs_executado": True,
        "incluir_evidencias": True,
        "incluir_divergencias": True,
        "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"],
    },
    "doubt": None,
}

payload = json.dumps(plan, ensure_ascii=False)
print(plan_validator(payload))
print(create_hitl_checkpoint(payload))
'@ | uv run python -
```

**Evidencia esperada:** `plan_validator` deve retornar `valid=True`, mas
`create_hitl_checkpoint` deve retornar `status: awaiting_human_validation` com
`execution_allowed: False`.

**Evidencia retornada:**

```text
{'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['receber_requisitos']}
{'status': 'awaiting_human_validation', 'checkpoint_id': 'HITL-CHK-001', 'execution_allowed': False, ...}
```

Funcionamento correto: o plano nao segue automaticamente quando a decisao de
autonomia indica `hitl_required`.

#### Teste 2.7

**Teste:** validar que uma acao com efeito externo, como disparar notificacao ou
e-mail de evidencia, nao deve ser executada automaticamente mesmo quando o plano
esta bem formado.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator, create_hitl_checkpoint

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {"nivel": "alto", "motivos": ["acao possui efeito externo e pode notificar pessoas fora do fluxo local"], "acoes_reversiveis": False, "efeito_externo": True},
    "autonomy_decision": {"mode": "hitl_required", "reason": "efeito externo exige aprovacao humana antes do envio", "less_prompt_more_action": False},
    "lifecycle": {"status": "aguardando_validacao_humana", "execution_allowed": False, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": True, "checkpoint_id": "HITL-CHK-002", "pause_reason": "acao externa nao reversivel detectada", "approval_question": "Aprova a execucao da acao externa planejada?", "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"]},
    "analise_inicial": {"linguagem_suspeita": "desconhecida", "funcao_suspeita_do_codigo": None, "nivel_de_confianca": 0.7},
    "analise_progressiva": [{"observacao": "o plano cita envio de notificacao", "hipotese": "a acao pode afetar terceiros", "validacao_planejada": "bloquear execucao ate aprovacao"}],
    "criterios_verificaveis": ["efeito externo identificado", "checkpoint HITL criado"],
    "objetivo_qa": "Validar bloqueio de acao externa",
    "estrategia": ["classificar risco", "pausar para aprovacao"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "acao externa aprovada", "status": "pendente"}],
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

payload = json.dumps(plan, ensure_ascii=False)
print(plan_validator(payload))
print(create_hitl_checkpoint(payload))
'@ | uv run python -
```

**Evidencia esperada:** o plano deve ser valido, porem o checkpoint deve ficar em
`awaiting_human_validation`, com `execution_allowed=False`, por causa do efeito
externo.

**Evidencia retornada:**

```text
{'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['qa_runner_agent']}
{'status': 'awaiting_human_validation', 'checkpoint_id': 'HITL-CHK-002', 'execution_allowed': False, ...}
```

#### Teste 2.8

**Teste:** validar que uma operacao potencialmente destrutiva, como limpeza de
base, remocao de artefatos ou alteracao nao reversivel de estado, exige
intervencao humana.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator, create_hitl_checkpoint

plan = {
    "tipo_entrada": "codigo",
    "modo": "codigo",
    "tools": ["executar_pytest_tool"],
    "risk_assessment": {"nivel": "alto", "motivos": ["operacao pode remover dados ou artefatos usados como evidencia"], "acoes_reversiveis": False, "efeito_externo": False},
    "autonomy_decision": {"mode": "hitl_required", "reason": "acao destrutiva ou nao reversivel nao deve seguir sozinha", "less_prompt_more_action": False},
    "lifecycle": {"status": "aguardando_validacao_humana", "execution_allowed": False, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": True, "checkpoint_id": "HITL-CHK-003", "pause_reason": "risco de perda de dados ou evidencias", "approval_question": "Aprova executar a operacao nao reversivel?", "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"]},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": "cleanup", "nivel_de_confianca": 0.76},
    "analise_progressiva": [{"observacao": "o plano envolve limpeza antes do teste", "hipotese": "evidencias podem ser perdidas", "validacao_planejada": "exigir aprovacao humana"}],
    "criterios_verificaveis": ["risco destrutivo identificado", "execucao bloqueada"],
    "objetivo_qa": "Validar bloqueio de operacao nao reversivel",
    "estrategia": ["avaliar reversibilidade", "criar checkpoint HITL"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "aprovacao para limpeza registrada", "status": "pendente"}],
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

payload = json.dumps(plan, ensure_ascii=False)
print(plan_validator(payload))
print(create_hitl_checkpoint(payload))
'@ | uv run python -
```

**Evidencia esperada:** a tool de checkpoint deve impedir execucao automatica,
pois `acoes_reversiveis=False` em um plano de risco alto.

**Evidencia retornada:**

```text
{'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['executar_pytest_tool']}
{'status': 'awaiting_human_validation', 'checkpoint_id': 'HITL-CHK-003', 'execution_allowed': False, ...}
```

#### Teste 2.9

**Teste:** validar que entrada contendo segredo, credencial ou dado sensivel deve
ser tratada como risco alto e exigir revisao humana antes do handoff ou execucao.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator, create_hitl_checkpoint

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["receber_requisitos"],
    "risk_assessment": {"nivel": "alto", "motivos": ["entrada aparenta conter credencial ou dado sensivel"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "hitl_required", "reason": "dado sensivel precisa ser revisado antes de continuar", "less_prompt_more_action": False},
    "lifecycle": {"status": "aguardando_validacao_humana", "execution_allowed": False, "next_step": "revisar_plano"},
    "hitl_checkpoint": {"required": True, "checkpoint_id": "HITL-CHK-004", "pause_reason": "possivel segredo ou dado sensivel no input", "approval_question": "Aprova continuar apos revisar e tratar o dado sensivel?", "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"]},
    "analise_inicial": {"linguagem_suspeita": "desconhecida", "funcao_suspeita_do_codigo": None, "nivel_de_confianca": 0.62},
    "analise_progressiva": [{"observacao": "o input contem padrao compativel com segredo", "hipotese": "o dado nao deve ser propagado para outro agente sem revisao", "validacao_planejada": "pausar e pedir revisao humana"}],
    "criterios_verificaveis": ["dado sensivel detectado", "handoff bloqueado ate revisao"],
    "objetivo_qa": "Validar protecao de dado sensivel no planejamento",
    "estrategia": ["marcar risco alto", "interromper autonomia", "pedir revisao"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "dado sensivel revisado", "status": "pendente"}],
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

payload = json.dumps(plan, ensure_ascii=False)
print(plan_validator(payload))
print(create_hitl_checkpoint(payload))
'@ | uv run python -
```

**Evidencia esperada:** o plano deve ser validado estruturalmente, mas nao deve
liberar execucao nem handoff automatico enquanto o dado sensivel nao for revisto.

**Evidencia retornada:**

```text
{'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['receber_requisitos']}
{'status': 'awaiting_human_validation', 'checkpoint_id': 'HITL-CHK-004', 'execution_allowed': False, ...}
```

#### Teste 2.10

**Teste:** validar que uma solicitacao fora do escopo de QA, como alterar codigo
de producao em vez de apenas planejar ou testar, exige handoff controlado e
aprovacao humana.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator, create_hitl_checkpoint

plan = {
    "tipo_entrada": "codigo",
    "modo": "codigo",
    "tools": ["code_fix_agent"],
    "risk_assessment": {"nivel": "alto", "motivos": ["solicitacao pode alterar codigo de producao fora do escopo direto de QA"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "hitl_required", "reason": "mudanca de producao precisa de aprovacao antes do handoff", "less_prompt_more_action": False},
    "lifecycle": {"status": "aguardando_validacao_humana", "execution_allowed": False, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": True, "checkpoint_id": "HITL-CHK-005", "pause_reason": "acao fora do escopo direto de QA detectada", "approval_question": "Aprova encaminhar a alteracao de codigo de producao para o subagente?", "allowed_decisions": ["aprovar", "rejeitar", "solicitar_ajustes"]},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": "servico de producao", "nivel_de_confianca": 0.72},
    "analise_progressiva": [{"observacao": "o plano envolve alterar implementacao e nao apenas teste", "hipotese": "a autonomia pode extrapolar o escopo de QA", "validacao_planejada": "bloquear ate aprovacao"}],
    "criterios_verificaveis": ["escopo de QA avaliado", "handoff condicionado a aprovacao"],
    "objetivo_qa": "Validar controle de escopo antes de handoff para correcao",
    "estrategia": ["identificar extrapolacao de escopo", "criar checkpoint HITL"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "aprovacao para handoff registrada", "status": "pendente"}],
    "handoff_context": {"objetivo": "avaliar possivel correcao de codigo", "contexto_compacto": "solicitacao envolve codigo de producao e precisa de aprovacao", "artefatos_relevantes": ["servico de producao"], "decisoes_tomadas": ["exigir HITL antes do handoff"], "riscos_e_duvidas": ["fora do escopo direto de QA"], "evidencias_necessarias": ["aprovacao humana"]},
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

payload = json.dumps(plan, ensure_ascii=False)
print(plan_validator(payload))
print(create_hitl_checkpoint(payload))
'@ | uv run python -
```

**Evidencia esperada:** o plano deve permanecer bloqueado para execucao, mesmo
com `handoff_context` preenchido, porque a decisao de autonomia e
`hitl_required`.

**Evidencia retornada:**

```text
{'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['code_fix_agent']}
{'status': 'awaiting_human_validation', 'checkpoint_id': 'HITL-CHK-005', 'execution_allowed': False, ...}
```


## Subtask 3 - Handoff inter-agentes

### Mudanca aplicada

Arquivos alterados:

- `agents/roles/qa_agent/qa_prompt.py`
- `agents/roles/qa_agent/subagents/action_planner/prompt.py`
- `agents/roles/qa_agent/tools/planner_tools.py`

O prompt principal agora orienta que handoffs para subagentes repassem:

- objetivo;
- contexto;
- artefatos;
- decisoes;
- riscos;
- evidencias esperadas.

O `action_planner` passou a estruturar esse pacote no campo
`handoff_context`, e o `plan_validator` valida esse campo quando ele esta
presente.

O catalogo de tools do planner tambem foi ampliado para incluir tools e
subagentes usados pelo `qa_agent`:

- `receber_requisitos`;
- `executar_pytest_tool`;
- `DoubtArtifactGenerator.generate`;
- `qa_runner_agent`;
- `code_fix_agent`.

### Como foi testado

#### Teste 3.1

**Teste:** validar se o catalogo do planner reconhece as tools e subagentes
envolvidos em handoff.

```powershell
@'
from agents.roles.qa_agent.tools.planner_tools import list_available_tools, describe_tools

print(list_available_tools("qa_agent"))
print(describe_tools("qa_runner_agent,code_fix_agent,DoubtArtifactGenerator.generate"))
'@ | uv run python -
```

**Evidencia esperada:** o retorno deve incluir `qa_runner_agent`,
`code_fix_agent` e `DoubtArtifactGenerator.generate`, com descricoes que
declaram contratos de entrada para handoff.

**Evidencia retornada:** o retorno incluiu:

- `qa_runner_agent`;
- `code_fix_agent`;
- `DoubtArtifactGenerator.generate`.

As descricoes dessas tools/subagentes passaram a declarar contratos de entrada
com pacote de handoff, incluindo requisito, criterios verificaveis, artefatos,
log pytest, plano original e divergencias quando aplicavel.

#### Teste 3.2

**Teste:** validar um plano com `handoff_context` completo, simulando a passagem
de contexto do `action_planner` para o `qa_runner_agent`.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {
        "nivel": "baixo",
        "motivos": ["handoff local para geracao e execucao de pytest"],
        "acoes_reversiveis": True,
        "efeito_externo": False
    },
    "autonomy_decision": {
        "mode": "autonomous",
        "reason": "acao local e reversivel",
        "less_prompt_more_action": True
    },
    "lifecycle": {
        "status": "planejado_para_execucao",
        "execution_allowed": True,
        "next_step": "executar_plano"
    },
    "hitl_checkpoint": {
        "required": False,
        "checkpoint_id": None,
        "pause_reason": None,
        "approval_question": None,
        "allowed_decisions": []
    },
    "analise_inicial": {
        "linguagem_suspeita": "python",
        "funcao_suspeita_do_codigo": None,
        "nivel_de_confianca": 0.8
    },
    "analise_progressiva": [
        {
            "observacao": "requisito de login recebido",
            "hipotese": "qa_runner_agent deve gerar e executar pytest",
            "validacao_planejada": "validar resultado da suite"
        }
    ],
    "criterios_verificaveis": ["login valido", "login invalido", "campos vazios"],
    "objetivo_qa": "Gerar e executar testes de login",
    "estrategia": ["enviar handoff ao qa_runner_agent", "executar pytest"],
    "checklist_inicial": [
        {"id": "CHK-01", "descricao": "handoff contem contexto minimo", "status": "pendente"}
    ],
    "handoff_context": {
        "objetivo": "Gerar e executar testes de login",
        "contexto_compacto": "RF-001: validar login com sucesso, falha e campos vazios",
        "artefatos_relevantes": ["RF-001"],
        "decisoes_tomadas": ["usar qa_runner_agent"],
        "riscos_e_duvidas": [],
        "evidencias_necessarias": ["arquivo pytest gerado", "resultado pytest"]
    },
    "relatorio_conformidade_esperado": {
        "comparar_planejado_vs_executado": True,
        "incluir_evidencias": True,
        "incluir_divergencias": True,
        "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]
    },
    "doubt": None
}

print(plan_validator(json.dumps(plan, ensure_ascii=False)))
'@ | uv run python -
```

**Evidencia esperada:** `plan_validator` deve retornar `valid=True` e
`errors=[]`.

**Evidencia retornada:** o `plan_validator` retornou:

```text
'valid': True
'errors': []
```

Isso confirma que um handoff completo e bem estruturado e aceito antes da
execucao.

#### Teste 3.3

**Teste:** validar o caso negativo removendo um campo obrigatorio do
`handoff_context`. Neste teste, o campo removido foi:

```python
"evidencias_necessarias": ["arquivo pytest gerado", "resultado pytest"]
```

O restante do plano foi mantido igual ao teste anterior.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {
        "nivel": "baixo",
        "motivos": ["handoff local para geracao e execucao de pytest"],
        "acoes_reversiveis": True,
        "efeito_externo": False
    },
    "autonomy_decision": {
        "mode": "autonomous",
        "reason": "acao local e reversivel",
        "less_prompt_more_action": True
    },
    "lifecycle": {
        "status": "planejado_para_execucao",
        "execution_allowed": True,
        "next_step": "executar_plano"
    },
    "hitl_checkpoint": {
        "required": False,
        "checkpoint_id": None,
        "pause_reason": None,
        "approval_question": None,
        "allowed_decisions": []
    },
    "analise_inicial": {
        "linguagem_suspeita": "python",
        "funcao_suspeita_do_codigo": None,
        "nivel_de_confianca": 0.8
    },
    "analise_progressiva": [
        {
            "observacao": "requisito de login recebido",
            "hipotese": "qa_runner_agent deve gerar e executar pytest",
            "validacao_planejada": "validar resultado da suite"
        }
    ],
    "criterios_verificaveis": ["login valido", "login invalido", "campos vazios"],
    "objetivo_qa": "Gerar e executar testes de login",
    "estrategia": ["enviar handoff ao qa_runner_agent", "executar pytest"],
    "checklist_inicial": [
        {"id": "CHK-01", "descricao": "handoff contem contexto minimo", "status": "pendente"}
    ],
    "handoff_context": {
        "objetivo": "Gerar e executar testes de login",
        "contexto_compacto": "RF-001: validar login com sucesso, falha e campos vazios",
        "artefatos_relevantes": ["RF-001"],
        "decisoes_tomadas": ["usar qa_runner_agent"],
        "riscos_e_duvidas": []
    },
    "relatorio_conformidade_esperado": {
        "comparar_planejado_vs_executado": True,
        "incluir_evidencias": True,
        "incluir_divergencias": True,
        "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]
    },
    "doubt": None
}

print(plan_validator(json.dumps(plan, ensure_ascii=False)))
'@ | uv run python -
```

**Evidencia esperada:** `plan_validator` deve retornar `valid=False` e apontar
`handoff_context incompleto: evidencias_necessarias`.

**Evidencia retornada:** o `plan_validator` retornou erro de handoff incompleto:

```text
'valid': False
handoff_context incompleto: evidencias_necessarias
```

Isso confirma que o validador consegue barrar um handoff que perderia contexto
importante antes de transferir a execucao para outro subagente.

#### Teste 3.4

**Teste:** listar as tools disponiveis para `qa_agent` e descrever
`qa_runner_agent`.

```powershell
@'
from agents.roles.qa_agent.tools.planner_tools import list_available_tools, describe_tools

print(list_available_tools("qa_agent"))
print(describe_tools("qa_runner_agent"))
'@ | uv run python -
```

**Evidencia esperada:** o catalogo deve incluir `qa_runner_agent`, e a descricao
deve mencionar contrato de entrada com contexto suficiente para handoff.

**Evidencia retornada:**
{'agent': 'qa_agent', 'total': 5, 'tools': [{'name': 'receber_requisitos', 'agent': 'qa_agent', 'category': 'requirements_to_pytest', 'summary': 'Recebe artefatos RF, HU, UC, RNF ou RN em JSON e gera suites pytest.'}, {'name': 'executar_pytest_tool', 'agent': 'qa_agent', 'category': 'pytest_execution', 'summary': 'Executa pytest em um arquivo especifico e retorna resultado estruturado.'}, {'name': 'DoubtArtifactGenerator.generate', 'agent': 'qa_agent', 'category': 'doubt_artifact', 'summary': 'Documenta bloqueios tecnicos quando um artefato nao permite acao segura.'}, {'name': 'qa_runner_agent', 'agent': 'qa_agent', 'category': 'test_generation_and_execution', 'summary': 'Subagente que gera teste a partir de HU/requisito e audita via pytest.'}, {'name': 'code_fix_agent', 'agent': 'qa_agent', 'category': 'test_failure_fix_prompt', 'summary': 'Analisa logs de erro e cria prompt de correcao para agente codificador.'}]}
{'agent': 'qa_agent', 'tools': [{'name': 'qa_runner_agent', 'agent': 'qa_agent', 'category': 'test_generation_and_execution', 'summary': 'Subagente que gera teste a partir de HU/requisito e audita via pytest.', 'input_contract': 'Pacote de handoff com requisito/HU, criterios verificaveis, artefatos relevantes e objetivo de cobertura.', 'output_contract': 'Payload com arquivo gerado, status de execucao, erros e proxima acao quando houver falha corrigivel.', 'use_when': ['O fluxo precisa gerar teste e executar pytest em sequencia.', 'O plano exige evidencias de sucesso, falha ou cobertura.'], 'avoid_when': ['Ja existe apenas um arquivo pytest para executar diretamente.', 'A entrada ainda precisa de triagem ou esta bloqueada por duvida real.']}], 'unknown_tools': []}

#### Teste 3.5

**Teste:** descrever uma tool inexistente junto com `qa_runner_agent`.

```powershell
@'
from agents.roles.qa_agent.tools.planner_tools import describe_tools

print(describe_tools("tool_inexistente,qa_runner_agent"))
'@ | uv run python -
```

**Evidencia esperada:** a tool inexistente deve ser tratada sem quebrar o fluxo,
e `qa_runner_agent` deve aparecer corretamente no retorno.

**Evidencia retornada:** {'agent': 'qa_agent', 'tools': [{'name': 'qa_runner_agent', 'agent': 'qa_agent', 'category': 'test_generation_and_execution', 'summary': 'Subagente que gera teste a partir de HU/requisito e audita via pytest.', 'input_contract': 'Pacote de handoff com requisito/HU, criterios verificaveis, artefatos relevantes e objetivo de cobertura.', 'output_contract': 'Payload com arquivo gerado, status de execucao, erros e proxima acao quando houver falha corrigivel.', 'use_when': ['O fluxo precisa gerar teste e executar pytest em sequencia.', 'O plano exige evidencias de sucesso, falha ou cobertura.'], 'avoid_when': ['Ja existe apenas um arquivo pytest para executar diretamente.', 'A entrada ainda precisa de triagem ou esta bloqueada por duvida real.']}], 'unknown_tools': ['tool_inexistente']}

#### Teste 3.6

**Teste:** validar um plano completo para handoff ao `code_fix_agent` apos falha
de pytest, incluindo log de erro em `artefatos_relevantes`.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator

plan = {
    "tipo_entrada": "codigo",
    "modo": "codigo",
    "tools": ["code_fix_agent"],
    "risk_assessment": {"nivel": "baixo", "motivos": ["handoff local para correcao de falha pytest"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "autonomous", "reason": "falha local corrigivel", "less_prompt_more_action": True},
    "lifecycle": {"status": "planejado_para_execucao", "execution_allowed": True, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": False, "checkpoint_id": None, "pause_reason": None, "approval_question": None, "allowed_decisions": []},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": "teste pytest", "nivel_de_confianca": 0.82},
    "analise_progressiva": [{"observacao": "pytest retornou falha corrigivel", "hipotese": "code_fix_agent deve receber log e contexto", "validacao_planejada": "validar handoff completo"}],
    "criterios_verificaveis": ["log pytest presente", "arquivo afetado presente", "divergencia informada"],
    "objetivo_qa": "Preparar handoff para code_fix_agent",
    "estrategia": ["compactar contexto", "encaminhar log ao code_fix_agent"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "handoff de correcao completo", "status": "pendente"}],
    "handoff_context": {
        "objetivo": "Corrigir falha pytest",
        "contexto_compacto": "Teste de login falhou por assercao divergente",
        "artefatos_relevantes": ["tests/test_login.py", "pytest: AssertionError"],
        "decisoes_tomadas": ["usar code_fix_agent"],
        "riscos_e_duvidas": [],
        "evidencias_necessarias": ["prompt de correcao", "resultado pytest apos ajuste"]
    },
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

print(plan_validator(json.dumps(plan, ensure_ascii=False)))
'@ | uv run python -
```

**Evidencia esperada:** o plano deve ser valido quando o contexto de correcao,
decisoes, riscos e evidencias estiverem presentes.

**Evidencia retornada:** {'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['code_fix_agent']}

#### Teste 3.7

**Teste:** validar um plano removendo `objetivo` de `handoff_context`.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {"nivel": "baixo", "motivos": ["teste negativo de handoff"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "autonomous", "reason": "validar campo obrigatorio ausente", "less_prompt_more_action": True},
    "lifecycle": {"status": "planejado_para_execucao", "execution_allowed": True, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": False, "checkpoint_id": None, "pause_reason": None, "approval_question": None, "allowed_decisions": []},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": None, "nivel_de_confianca": 0.8},
    "analise_progressiva": [{"observacao": "handoff sem objetivo", "hipotese": "validador deve barrar", "validacao_planejada": "inspecionar errors"}],
    "criterios_verificaveis": ["campo objetivo obrigatorio"],
    "objetivo_qa": "Validar handoff sem objetivo",
    "estrategia": ["remover objetivo", "validar plano"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "erro de objetivo ausente detectado", "status": "pendente"}],
    "handoff_context": {"contexto_compacto": "RF de login", "artefatos_relevantes": ["RF-001"], "decisoes_tomadas": ["usar qa_runner_agent"], "riscos_e_duvidas": [], "evidencias_necessarias": ["erro do validador"]},
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

print(plan_validator(json.dumps(plan, ensure_ascii=False)))
'@ | uv run python -
```

**Evidencia esperada:** `plan_validator` deve retornar `valid=False` e apontar
`handoff_context incompleto: objetivo`.

**Evidencia retornada:** {'valid': False, 'errors': ['handoff_context incompleto: objetivo'], 'warnings': [], 'selected_tools': ['qa_runner_agent']}

#### Teste 3.8

**Teste:** validar um plano removendo `contexto_compacto` de
`handoff_context`.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {"nivel": "baixo", "motivos": ["teste negativo de handoff"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "autonomous", "reason": "validar contexto ausente", "less_prompt_more_action": True},
    "lifecycle": {"status": "planejado_para_execucao", "execution_allowed": True, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": False, "checkpoint_id": None, "pause_reason": None, "approval_question": None, "allowed_decisions": []},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": None, "nivel_de_confianca": 0.8},
    "analise_progressiva": [{"observacao": "handoff sem contexto compacto", "hipotese": "validador deve barrar", "validacao_planejada": "inspecionar errors"}],
    "criterios_verificaveis": ["campo contexto_compacto obrigatorio"],
    "objetivo_qa": "Validar handoff sem contexto_compacto",
    "estrategia": ["remover contexto_compacto", "validar plano"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "erro de contexto ausente detectado", "status": "pendente"}],
    "handoff_context": {"objetivo": "Gerar testes de login", "artefatos_relevantes": ["RF-001"], "decisoes_tomadas": ["usar qa_runner_agent"], "riscos_e_duvidas": [], "evidencias_necessarias": ["erro do validador"]},
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

print(plan_validator(json.dumps(plan, ensure_ascii=False)))
'@ | uv run python -
```

**Evidencia esperada:** o validador deve rejeitar o plano e indicar que
`contexto_compacto` esta ausente.

**Evidencia retornada:** {'valid': False, 'errors': ['handoff_context incompleto: contexto_compacto'], 'warnings': [], 'selected_tools': ['qa_runner_agent']}

#### Teste 3.9

**Teste:** validar um plano com `handoff_context` vazio `{}`.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {"nivel": "baixo", "motivos": ["teste de comportamento atual com handoff vazio"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "autonomous", "reason": "validar comportamento atual do validador", "less_prompt_more_action": True},
    "lifecycle": {"status": "planejado_para_execucao", "execution_allowed": True, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": False, "checkpoint_id": None, "pause_reason": None, "approval_question": None, "allowed_decisions": []},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": None, "nivel_de_confianca": 0.8},
    "analise_progressiva": [{"observacao": "handoff_context vazio", "hipotese": "nao deve disparar erro especifico de campos faltantes", "validacao_planejada": "inspecionar errors"}],
    "criterios_verificaveis": ["validador nao acusa handoff incompleto vazio"],
    "objetivo_qa": "Validar comportamento com handoff vazio",
    "estrategia": ["usar handoff_context vazio", "validar plano"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "plano validado com handoff vazio", "status": "pendente"}],
    "handoff_context": {},
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

print(plan_validator(json.dumps(plan, ensure_ascii=False)))
'@ | uv run python -
```

**Evidencia esperada:** pelo comportamento atual, o validador nao deve acusar
erro especifico de handoff incompleto quando o objeto esta vazio, pois a
validacao de campos so ocorre quando `handoff_context` possui conteudo.

**Evidencia retornada:** {'valid': True, 'errors': [], 'warnings': [], 'selected_tools': ['qa_runner_agent']}

#### Teste 3.10

**Teste:** validar um plano com `handoff_context` contendo
`artefatos_relevantes` como string em vez de lista.

```powershell
@'
import json
from agents.roles.qa_agent.tools.planner_tools import plan_validator

plan = {
    "tipo_entrada": "requisito",
    "modo": "requisito",
    "tools": ["qa_runner_agent"],
    "risk_assessment": {"nivel": "baixo", "motivos": ["teste negativo de tipo no handoff"], "acoes_reversiveis": True, "efeito_externo": False},
    "autonomy_decision": {"mode": "autonomous", "reason": "validar tipo de lista", "less_prompt_more_action": True},
    "lifecycle": {"status": "planejado_para_execucao", "execution_allowed": True, "next_step": "executar_plano"},
    "hitl_checkpoint": {"required": False, "checkpoint_id": None, "pause_reason": None, "approval_question": None, "allowed_decisions": []},
    "analise_inicial": {"linguagem_suspeita": "python", "funcao_suspeita_do_codigo": None, "nivel_de_confianca": 0.8},
    "analise_progressiva": [{"observacao": "artefatos_relevantes veio como string", "hipotese": "validador deve barrar tipo invalido", "validacao_planejada": "inspecionar errors"}],
    "criterios_verificaveis": ["artefatos_relevantes deve ser lista"],
    "objetivo_qa": "Validar tipo de artefatos_relevantes",
    "estrategia": ["usar tipo invalido", "validar plano"],
    "checklist_inicial": [{"id": "CHK-01", "descricao": "erro de tipo detectado", "status": "pendente"}],
    "handoff_context": {"objetivo": "Gerar testes", "contexto_compacto": "RF de login", "artefatos_relevantes": "RF-001", "decisoes_tomadas": ["usar qa_runner_agent"], "riscos_e_duvidas": [], "evidencias_necessarias": ["erro do validador"]},
    "relatorio_conformidade_esperado": {"comparar_planejado_vs_executado": True, "incluir_evidencias": True, "incluir_divergencias": True, "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"]},
    "doubt": None,
}

print(plan_validator(json.dumps(plan, ensure_ascii=False)))
'@ | uv run python -
```

**Evidencia esperada:** `plan_validator` deve retornar `valid=False` e apontar
que `handoff_context.artefatos_relevantes deve ser lista`.

**Evidencia retornada:** {'valid': False, 'errors': ['handoff_context.artefatos_relevantes deve ser lista.'], 'warnings': [], 'selected_tools': ['qa_runner_agent']}

## Status final

P1 implementado e validado em nivel funcional:

- o `action_planner` foi observado sendo chamado antes do restante do fluxo;
- o planejamento passou a diferenciar execucao autonoma de HITL;
- o handoff passou a ter estrutura explicita para reduzir perda de contexto;
