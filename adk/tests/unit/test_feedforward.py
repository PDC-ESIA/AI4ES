"""Testes da camada de feedforward (issue #303).

Cobrem `build_context_pack`, `selecionar_stack` e `_secoes` — funções puras, sem
ADK, sem rede. O `_ContextProvisioner` em si não é exercitado aqui: ele só grava
`state_delta` e um arquivo, e toda a lógica que pode errar está nas funções.

Não há caso de "orçamento de tokens atingido": o pack acumula por padrão
(*grow-and-refine*) em vez de comprimir para caber num alvo fixo — ver §5.4 e §8.2
do relatório da camada. O que se testa no lugar é justamente a AUSÊNCIA de truncagem.
"""

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from shared.workspace import AGENT_DIRS
from src.agents.workflow_coding_review import cr_feedforward
from src.agents.workflow_coding_review.cr_feedforward import (
    _linha_auditoria,
    _secoes,
    agent as agente_feedforward,
    build_context_pack,
    selecionar_stack,
)

_FASTAPI = ["Python", "FastAPI", "SQLAlchemy"]


def _escrever(caminho: Path, texto: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")


@pytest.fixture
def kb(tmp_path: Path) -> Path:
    """KB mínima: um item por arquivo, o suficiente para observar ordem e dedup."""
    raiz = tmp_path / "knowledge"
    _escrever(
        raiz / "core" / "conventions.md",
        "# Convenções\n\nPreâmbulo ignorado.\n\n## SRP\n\nDivida arquivos grandes.\n",
    )
    _escrever(
        raiz / "core" / "consistency-rules.md",
        "# Regras\n\n## Imports no manifesto\n\nDeclare o que importa.\n",
    )
    _escrever(raiz / "core" / "lessons.md", "")  # nasce vazio, como no repo
    _escrever(
        raiz / "stacks" / "python-fastapi" / "pitfalls.md",
        "# Pitfalls\n\n## ForeignKey\n\nRelationship exige FK.\n",
    )
    _escrever(
        raiz / "stacks" / "python-fastapi" / "deps.md",
        "# Deps\n\n## Pacotes bons\n\nfastapi, uvicorn.\n",
    )
    _escrever(raiz / "stacks" / "python-fastapi" / "lessons.md", "")
    return raiz


# ---------------------------------------------------------------------------
# Seleção de escopo
# ---------------------------------------------------------------------------


def test_stack_reconhecida_traz_core_e_stack(kb: Path):
    pack = build_context_pack(_FASTAPI, kb)

    assert "## Imports no manifesto" in pack
    assert "## SRP" in pack
    assert "## ForeignKey" in pack
    assert "## Pacotes bons" in pack
    assert "# Conhecimento — stack `python-fastapi`" in pack


def test_stack_desconhecida_traz_so_core(kb: Path):
    pack = build_context_pack(["Go", "Gin"], kb)

    assert "## Imports no manifesto" in pack
    assert "## ForeignKey" not in pack
    assert "stack `" not in pack


def test_tech_stack_a_definir_traz_so_core(kb: Path):
    """`['a definir']` é o fallback documentado do context_engineer."""
    pack = build_context_pack(["a definir"], kb)

    assert "## Imports no manifesto" in pack
    assert "## ForeignKey" not in pack


def test_tech_stack_vazio_traz_so_core(kb: Path):
    pack = build_context_pack([], kb)

    assert "## Imports no manifesto" in pack
    assert "## ForeignKey" not in pack


def test_knowledge_root_inexistente_devolve_vazio_sem_excecao(tmp_path: Path):
    assert build_context_pack(_FASTAPI, tmp_path / "nao-existe") == ""


def test_arquivo_vazio_nao_entra_no_pack(kb: Path):
    """`lessons.md` nasce vazio e não deve poluir o pack com cabeçalho órfão."""
    pack = build_context_pack(_FASTAPI, kb)

    assert "lessons" not in pack


def test_md_nao_utf8_e_pulado_sem_derrubar_o_pack(kb: Path, caplog):
    """A KB é editada à mão; um `.md` em latin-1 não pode abortar o pipeline."""
    (kb / "core" / "conventions.md").write_bytes(
        "# Convenções\n\n## Acentuação\n\nNão gere monolitos.\n".encode("latin-1")
    )

    with caplog.at_level(logging.WARNING):
        pack = build_context_pack(_FASTAPI, kb)

    assert "ilegível" in caplog.text
    assert "## Acentuação" not in pack
    # o resto da KB sobrevive — não é tudo-ou-nada
    assert "## Imports no manifesto" in pack
    assert "## ForeignKey" in pack


# ---------------------------------------------------------------------------
# Acúmulo, ordem e dedup
# ---------------------------------------------------------------------------


def test_pack_acumula_sem_truncar(kb: Path):
    """Grow-and-refine: todo item entra, nada é comprimido."""
    pack = build_context_pack(_FASTAPI, kb)

    for corpo in (
        "Divida arquivos grandes.",
        "Declare o que importa.",
        "Relationship exige FK.",
        "fastapi, uvicorn.",
    ):
        assert corpo in pack


def test_determinismo(kb: Path):
    assert build_context_pack(_FASTAPI, kb) == build_context_pack(_FASTAPI, kb)


def test_dedup_item_repetido_entre_core_e_stack(kb: Path):
    """Mesmo título em `core/` e em `stacks/` → aparece uma única vez."""
    _escrever(
        kb / "stacks" / "python-fastapi" / "pitfalls.md",
        "# Pitfalls\n\n## Imports no manifesto\n\nVersão da stack.\n"
        "\n## ForeignKey\n\nRelationship exige FK.\n",
    )

    pack = build_context_pack(_FASTAPI, kb)

    assert pack.count("## Imports no manifesto") == 1
    assert "## ForeignKey" in pack


def test_dedup_preserva_a_versao_de_core(kb: Path):
    """`core/` é montado primeiro, então o item promovido a core é o que sobrevive."""
    _escrever(
        kb / "stacks" / "python-fastapi" / "pitfalls.md",
        "# Pitfalls\n\n## Imports no manifesto\n\nVersão da stack.\n",
    )

    pack = build_context_pack(_FASTAPI, kb)

    assert "Declare o que importa." in pack
    assert "Versão da stack." not in pack


def test_ordem_prioriza_regra_acionavel_sobre_referencia(kb: Path):
    """`consistency-rules` antes de `conventions`; `pitfalls` antes de `deps`."""
    pack = build_context_pack(_FASTAPI, kb)

    assert pack.index("## Imports no manifesto") < pack.index("## SRP")
    assert pack.index("## ForeignKey") < pack.index("## Pacotes bons")


def test_core_vem_antes_da_stack(kb: Path):
    pack = build_context_pack(_FASTAPI, kb)

    assert pack.index("# Conhecimento — core") < pack.index("# Conhecimento — stack")


# ---------------------------------------------------------------------------
# Quebra em itens
# ---------------------------------------------------------------------------


def test_secoes_descarta_titulo_do_arquivo_e_preambulo():
    secoes = _secoes("# Título do arquivo\n\nPreâmbulo.\n\n## Item A\n\nCorpo A.\n")

    assert [titulo for titulo, _ in secoes] == ["Item A"]
    assert "Preâmbulo." not in secoes[0][1]
    assert "Título do arquivo" not in secoes[0][1]


def test_secoes_sem_nenhum_item_devolve_lista_vazia():
    assert _secoes("# Só o título\n\nProsa solta, sem `##`.\n") == []


# ---------------------------------------------------------------------------
# Casamento de stack — texto livre gerado por LLM
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tech_stack",
    [
        ["Python", "FastAPI", "SQLAlchemy"],
        ["fastapi"],
        ["FastAPI 0.111"],
        ["Python/FastAPI/SQLAlchemy"],
        ["Backend: FastAPI + Jinja2"],
    ],
    ids=["lista-limpa", "minusculo", "com-versao", "string-composta", "prosa"],
)
def test_selecionar_stack_casa_por_substring(tech_stack):
    assert selecionar_stack(tech_stack) == "python-fastapi"


@pytest.mark.parametrize(
    "tech_stack",
    [[], ["a definir"], ["Go", "Gin"], ["Node.js", "Express"]],
    ids=["vazio", "a-definir", "go", "node"],
)
def test_selecionar_stack_sem_match_devolve_none(tech_stack):
    assert selecionar_stack(tech_stack) is None


def test_tech_stack_com_item_nao_string_nao_quebra():
    assert selecionar_stack([None, 42, "FastAPI"]) == "python-fastapi"


def test_stack_nao_reconhecida_emite_warning(kb: Path, caplog):
    """Cair em core/ deixou de ser inócuo — o coder perde deps.md/pitfalls.md."""
    with caplog.at_level(logging.WARNING):
        build_context_pack(["Go", "Gin"], kb)

    assert "stack não reconhecida" in caplog.text


def test_stack_reconhecida_nao_emite_warning(kb: Path, caplog):
    with caplog.at_level(logging.WARNING):
        build_context_pack(_FASTAPI, kb)

    assert caplog.text == ""


# ---------------------------------------------------------------------------
# Auditoria e fiação
# ---------------------------------------------------------------------------


def test_linha_auditoria_registra_recebido_e_selecionado():
    linha = _linha_auditoria(["Python", "FastAPI"], "python-fastapi")

    assert linha.startswith("<!--")
    assert "FastAPI" in linha
    assert "python-fastapi" in linha


def test_linha_auditoria_registra_stack_nao_seleciondada():
    assert "None" in _linha_auditoria(["a definir"], None)


def test_agent_dirs_mapeia_cr_feedforward():
    """Sem a entrada, `get_agent_workspace('cr_feedforward')` levanta ValueError."""
    assert AGENT_DIRS["cr_feedforward"] == "coder/context"


# ---------------------------------------------------------------------------
# KB real do repositório
# ---------------------------------------------------------------------------


def test_kb_real_carrega_core_e_stack_fastapi():
    """Contra `adk/knowledge/` de verdade — pega KB movida, quebrada ou vazia."""
    pack = build_context_pack(_FASTAPI)

    assert "# Conhecimento — core" in pack
    assert "# Conhecimento — stack `python-fastapi`" in pack
    assert "Responsabilidade Única" in pack
    assert "ForeignKey" in pack


def test_kb_real_sem_item_duplicado_entre_core_e_stack():
    """Regressão da limpeza de duplicação: nenhum título repetido no pack real."""
    pack = build_context_pack(_FASTAPI)
    titulos = [ln for ln in pack.splitlines() if ln.startswith("## ")]

    assert len(titulos) == len(set(titulos))


# ---------------------------------------------------------------------------
# O agente — é elo de um SequentialAgent, então exceção aqui aborta o pipeline
# ---------------------------------------------------------------------------


@pytest.fixture
def ws_isolado(tmp_path: Path, monkeypatch):
    """Impede que o teste escreva no `workspace_output/` real do repositório."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    return tmp_path


def _ctx(state: dict):
    """Stub de InvocationContext — o agente só usa session.state e invocation_id."""
    return SimpleNamespace(
        session=SimpleNamespace(state=state), invocation_id="inv-teste"
    )


async def _rodar(state: dict) -> list:
    return [ev async for ev in agente_feedforward._run_async_impl(_ctx(state))]


async def test_agente_grava_context_pack_no_state_delta(ws_isolado):
    eventos = await _rodar({"tasks": {"macro_context": {"tech_stack": _FASTAPI}}})

    assert len(eventos) == 1
    delta = eventos[0].actions.state_delta
    assert "Responsabilidade Única" in delta["context_pack"]
    assert Path(delta["context_pack_path"]).is_file()


async def test_agente_persiste_em_coder_context(ws_isolado):
    eventos = await _rodar({"tasks": {"macro_context": {"tech_stack": _FASTAPI}}})

    destino = Path(eventos[0].actions.state_delta["context_pack_path"])
    assert destino.parent == Path(ws_isolado / "ws" / "coder" / "context")
    assert destino.read_text(encoding="utf-8").startswith("<!--")


async def test_agente_nao_propaga_falha_da_kb(ws_isolado, monkeypatch, caplog):
    """KB quebrada degrada para pack vazio — nunca aborta o SequentialAgent."""

    def _explode(*_args, **_kwargs):
        raise RuntimeError("KB corrompida")

    monkeypatch.setattr(cr_feedforward, "build_context_pack", _explode)

    with caplog.at_level(logging.ERROR):
        eventos = await _rodar({"tasks": {"macro_context": {"tech_stack": _FASTAPI}}})

    assert eventos[0].actions.state_delta["context_pack"] == ""
    assert "degradação, não interrupção" in caplog.text


async def test_agente_tolera_tasks_ausente_ou_malformado(ws_isolado):
    """Sem `tasks` (ou com formato inesperado) o agente ainda entrega o core."""
    for state in ({}, {"tasks": None}, {"tasks": "texto solto"}, {"tasks": {}}):
        eventos = await _rodar(state)

        assert "context_pack" in eventos[0].actions.state_delta
