"""conftest.py — Camada 3 (evals, escopo coder_isolado).

`workspace_fixture` e `_requer_llm_real` vêm do ancestral
`tests/coder_isolado/conftest.py` (descoberta automática do pytest, sem
import) — este arquivo acrescenta o que é específico da avaliação do
`cr_review_analyzer` contra um dataset: popular `coder/src/` com código
para o reviewer ler, carregar/validar o dataset de casos e rodar o
LLM-judge que avalia a resposta do reviewer contra o gabarito de cada caso.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

import pytest
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import BaseModel


@pytest.fixture
def coder_workspace_com_codigo(
    workspace_fixture: Path,
) -> Callable[[dict[str, str]], Path]:
    """Factory: escreve `{nome_arquivo: conteudo}` em `<workspace>/coder/src/`.

    `cr_review_analyzer` lê o código a revisar via filesystem
    (`get_agent_workspace("cr_coder")` → `<WORKSPACE_OUTPUT_DIR>/coder/src`),
    não via `session.state` — por isso a fixture escreve direto no disco em
    vez de popular estado de sessão. Uso::

        def test_x(coder_workspace_com_codigo):
            coder_workspace_com_codigo({"app.py": "print(1)\\n"})
    """

    def _escrever(arquivos: dict[str, str]) -> Path:
        coder_src = workspace_fixture / "coder" / "src"
        coder_src.mkdir(parents=True, exist_ok=True)
        for nome, conteudo in arquivos.items():
            (coder_src / nome).write_text(conteudo, encoding="utf-8")
        return coder_src

    return _escrever


# ---------------------------------------------------------------------------
# Dataset — loader + validação de schema (roda na COLETA, não na execução)
# ---------------------------------------------------------------------------

_DATASET_DIR = Path(__file__).parent / "dataset"

_CHAVES_OBRIGATORIAS = (
    "id",
    "categoria",
    "descricao_curta",
    "arquivos",
    "arquivos_teste",
    "veredito_esperado",
    "severidade_esperada",
    "palavras_chave_deterministicas",
    "problema_para_judge",
)

_VEREDITOS_VALIDOS = {"BLOQUEADO", "APROVADO"}


def _validar_caso(caso: dict, origem: Path) -> None:
    """Levanta `ValueError` claro se `caso` não bate com o schema do dataset.

    Chamada durante `carregar_casos_dataset()` — que por sua vez é chamada
    dentro de `@pytest.mark.parametrize` no MOMENTO DA COLETA do pytest.
    Um `ValueError` aqui vira erro de coleta (`pytest --collect-only`
    falha, apontando este arquivo), não um teste silenciosamente pulado —
    de propósito, para um dataset malformado nunca passar despercebido.
    """
    faltando = [chave for chave in _CHAVES_OBRIGATORIAS if chave not in caso]
    if faltando:
        raise ValueError(
            f"{origem}: faltam chave(s) obrigatória(s) do schema: {faltando}"
        )
    if caso["veredito_esperado"] not in _VEREDITOS_VALIDOS:
        raise ValueError(
            f"{origem}: veredito_esperado={caso['veredito_esperado']!r} "
            f"inválido — esperado um de {sorted(_VEREDITOS_VALIDOS)}"
        )
    if not isinstance(caso["arquivos"], dict) or not caso["arquivos"]:
        raise ValueError(f"{origem}: 'arquivos' deve ser um dict não-vazio")
    if not isinstance(caso["arquivos_teste"], dict):
        raise ValueError(f"{origem}: 'arquivos_teste' deve ser um dict (pode ser {{}})")
    if not isinstance(caso["palavras_chave_deterministicas"], list):
        raise ValueError(f"{origem}: 'palavras_chave_deterministicas' deve ser uma lista")
    if caso["veredito_esperado"] == "BLOQUEADO" and not caso["palavras_chave_deterministicas"]:
        raise ValueError(
            f"{origem}: veredito_esperado=BLOQUEADO exige "
            f"'palavras_chave_deterministicas' não-vazia"
        )


def carregar_casos_dataset() -> list[dict]:
    """Lê e valida todos os `*.json` de `tests/coder_isolado/evals/dataset/`.

    Função pura (não fixture) — chamada diretamente dentro de
    `@pytest.mark.parametrize(..., carregar_casos_dataset(), ...)`, que o
    pytest avalia na COLETA. Isso é o que faz um JSON malformado falhar a
    coleta da suíte inteira em vez de só pular um caso.

    Returns:
        Lista de dicts (um por caso), ordenada por "id" para execução
        determinística.

    Raises:
        ValueError: se algum `*.json` não tiver as chaves obrigatórias do
            schema, tiver um valor inválido (ver `_validar_caso`), ou não
            for um JSON sintaticamente válido.
    """
    arquivos = sorted(_DATASET_DIR.glob("*.json"))
    casos = []
    for arquivo in arquivos:
        try:
            caso = json.loads(arquivo.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{arquivo}: JSON inválido — {exc}") from exc
        _validar_caso(caso, arquivo)
        casos.append(caso)
    return sorted(casos, key=lambda c: c["id"])


# ---------------------------------------------------------------------------
# LLM-judge — segunda camada de avaliação (semântica, não só palavra-chave)
# ---------------------------------------------------------------------------

class JudgeVerdict(BaseModel):
    """Veredito do LLM-judge sobre a resposta do reviewer para um caso.

    Local deste conftest — NÃO é um schema de produção (não vive em
    `src/agents/*/schemas.py`), existe só para este propósito de teste.
    """

    correto: bool
    justificativa: str


_JUDGE_INSTRUCTION = """
Você é um avaliador (judge) de qualidade que julga se um revisor de código
(LLM) avaliou CORRETAMENTE um trecho de código, comparando a saída real do
revisor com o problema esperado do caso (ou a confirmação de que o código
está correto).

Você recebe duas informações:
1. PROBLEMA ESPERADO: descrição objetiva do que deveria ser encontrado no
   código — OU, se o código está correto, uma frase confirmando isso (você
   reconhece esse caso porque a frase afirma que o código está correto/bem
   testado, sem descrever um problema real).
2. SAÍDA DO REVISOR: a resposta real (markdown) que o revisor produziu,
   incluindo a linha "## Status: APROVADO" ou "## Status: BLOQUEADO".

O critério de "correto" MUDA conforme o tipo de caso — use o texto do
PROBLEMA ESPERADO para saber qual dos dois blocos abaixo se aplica.

═══ CASO A — PROBLEMA ESPERADO confirma que o código está correto (caso
espera aprovação) ═══
Marque CORRETO se:
- a SAÍDA DO REVISOR tem "## Status: APROVADO"; E
- nenhuma issue de severidade alta/crítica foi inventada sobre um problema
  que não existe de fato no código.
Issues de severidade "warning"/"info" sobre estilo ou boas práticas
menores (ex.: sugestão de docstring, nomenclatura, preferir
`assert x == y` a `assert x`) são ACEITÁVEIS e NÃO tornam a avaliação
incorreta — um revisor atento que aprova mas aponta ressalvas menores está
se comportando bem, não mal.
Marque INCORRETO se:
- o status é BLOQUEADO quando deveria ser APROVADO; OU
- o revisor aprovou, mas a issue "menor" na verdade descreve um problema
  sério inventado/exagerado que não existe no código.

  Exemplo CORRETO: status "APROVADO", com uma issue de severidade "info"
  sugerindo adicionar docstring — ressalva menor, não invalida a
  aprovação.
  Exemplo INCORRETO: status "BLOQUEADO" citando um problema que não existe
  de fato no código (o código estava correto e deveria ter sido
  aprovado).

═══ CASO B — PROBLEMA ESPERADO descreve um problema real no código (caso
espera bloqueio) ═══
Marque CORRETO se:
- a SAÍDA DO REVISOR tem "## Status: BLOQUEADO"; E
- a explicação/issues capturam, EM ESSÊNCIA, o mesmo problema descrito em
  PROBLEMA ESPERADO — não precisa das mesmas palavras, só a mesma ideia
  central (a mesma causa raiz).
Marque INCORRETO se:
- o status é APROVADO quando deveria ser BLOQUEADO; OU
- o status é BLOQUEADO, mas pelo motivo ERRADO, ou só com uma
  justificativa genérica que não captura a causa raiz descrita em
  PROBLEMA ESPERADO.

  Exemplo CORRETO: PROBLEMA ESPERADO descreve SQL injection por
  concatenação de input do usuário; a saída do revisor bloqueia citando
  "query montada por concatenação de string do usuário, sem
  parametrização" — ideia central bate, palavras diferentes.
  Exemplo INCORRETO: PROBLEMA ESPERADO descreve SQL injection, mas a
  saída do revisor bloqueia só por "falta de docstring na função" —
  status bate (BLOQUEADO), mas o motivo é outro; não captura o problema
  real.

Responda EXCLUSIVAMENTE no schema esperado:
- correto: true/false conforme os critérios acima (CASO A ou CASO B,
  conforme o PROBLEMA ESPERADO).
- justificativa: 1-3 frases objetivas dizendo qual critério decidiu o
  resultado (ex.: "status errado", "motivo errado/genérico", "issue
  menor aceitável — aprovação correta", etc.).
""".strip()

_JUDGE_DEFAULT_MODEL = "gemini-2.5-flash"


@pytest.fixture
def _llm_judge():
    """Retorna `avaliar(problema_esperado, saida_reviewer) -> JudgeVerdict`.

    O `LlmAgent` de avaliação é construído aqui dentro, localmente — NÃO é
    um agente de produção, não vive em `src/agents/`, existe só para
    avaliar os testes desta camada. Lê `ADK_LLM_MODEL` com fallback para
    `_JUDGE_DEFAULT_MODEL`, mesmo padrão usado por todo `agent.py` de
    produção do projeto (ex.: `_model = os.environ.get("ADK_LLM_MODEL",
    _DEFAULT_MODEL)` em `reviewer/agent.py`, `coder/agent.py`, etc.).

    Roda via `Runner` + `InMemorySessionService` real, mesmo padrão do
    resto do projeto. Lê o veredito estruturado de `session.state`
    (populado por `output_key`, via `output_schema=JudgeVerdict`) — mesmo
    mecanismo de leitura de state pós-run usado em
    `tests/integration/test_hitl_e2e.py`.
    """
    modelo = os.environ.get("ADK_LLM_MODEL", _JUDGE_DEFAULT_MODEL)

    judge_agent = LlmAgent(
        model=modelo,
        name="eval_judge_agent",
        description=(
            "Avalia se a saída do cr_review_analyzer identificou "
            "corretamente o problema esperado de um caso de teste."
        ),
        instruction=_JUDGE_INSTRUCTION,
        output_schema=JudgeVerdict,
        output_key="judge_verdict",
    )

    async def _avaliar(problema_esperado: str, saida_reviewer: str) -> JudgeVerdict:
        runner = Runner(
            app_name="eval_judge",
            agent=judge_agent,
            session_service=InMemorySessionService(),
        )
        session = await runner.session_service.create_session(
            app_name="eval_judge", user_id="u", state={},
        )
        mensagem = (
            f"PROBLEMA ESPERADO:\n{problema_esperado}\n\n"
            f"SAÍDA DO REVISOR:\n{saida_reviewer}"
        )
        msg = types.Content(role="user", parts=[types.Part.from_text(text=mensagem)])
        async for _ in runner.run_async(user_id="u", session_id=session.id, new_message=msg):
            pass

        sessao_final = await runner.session_service.get_session(
            app_name="eval_judge", user_id="u", session_id=session.id,
        )
        await runner.close()

        veredito_bruto = sessao_final.state.get("judge_verdict")
        assert veredito_bruto is not None, (
            "judge_agent não populou session.state['judge_verdict'] — "
            "resposta do judge pode não ter batido com o output_schema."
        )
        return JudgeVerdict.model_validate(veredito_bruto)

    return _avaliar
