"""Testes do QA de critérios de aceite no loop (PoC issue #394).

O foco é o que é DETERMINÍSTICO: o portão sobre o código que o LLM escreve, a
montagem do spec, a leitura do relatório do Playwright e a tradução para o
vocabulário de critérios do harness. A geração em si (a chamada ao modelo) não é
exercitada aqui — o que se testa é que nada do que ela devolva escapa das
invariantes.
"""

from __future__ import annotations

import pytest

from shared.tools.coding_tools.criterios_aceite import AcceptanceCriterion
from shared.tools.coding_tools.harness_schemas import CriterionOutcome
from src.agents.workflow_coding_review.executor.qa_criterios.schemas import (
    CriterioNaoVerificavel,
    EspecificacaoCriterios,
    TesteDeCriterio,
)
from src.agents.workflow_coding_review.executor.qa_criterios.spec import (
    montar_evidencias,
    montar_spec,
    status_por_titulo,
    titulo_do_teste,
    validar_corpo,
)
from src.agents.workflow_coding_review.executor.qa_criterios.verificacao import (
    _chave_de_reuso,
    _filtrar_testes,
    _ler_spec_guardado,
    base_tecnica_comprovada,
)

_CORPO_OK = (
    "await page.goto('/');\n"
    "await expect(page.getByRole('heading', { name: 'Álbuns' })).toBeVisible();"
)


def _criterios(*ids: str) -> list[AcceptanceCriterion]:
    return [
        AcceptanceCriterion(id=i, description=f"Critério {i}", automatable=True)
        for i in ids
    ]


# ---------------------------------------------------------------------------
# validar_corpo — o portão sobre o que o LLM escreveu
# ---------------------------------------------------------------------------


def test_corpo_bem_formado_passa():
    assert validar_corpo(_CORPO_OK) is None


def test_interceptar_a_rede_invalida_a_prova():
    """`page.route` faz o teste passar contra resposta forjada por ele mesmo.

    É a recusa mais importante do portão: sem ela, o QA poderia "provar" um
    critério sem que a aplicação fizesse nada — recriando por outra via o vício
    de testar contra si mesmo que esta PoC existe para eliminar.
    """
    corpo = (
        "await page.route('**/api/albuns', r => r.fulfill({ body: '[]' }));\n"
        "await page.goto('/');\n"
        "await expect(page.locator('body')).toBeVisible();"
    )

    motivo = validar_corpo(corpo)

    assert motivo is not None
    assert "rede" in motivo


def test_injetar_html_proprio_invalida_a_prova():
    corpo = "await page.setContent('<h1>Álbuns</h1>');\nawait expect(page.locator('h1')).toBeVisible();"

    assert validar_corpo(corpo) is not None


@pytest.mark.parametrize(
    "corpo",
    [
        "import { x } from 'y';\nawait page.goto('/');\nexpect(1).toBe(1);",
        "const x = require('fs');\nawait page.goto('/');\nexpect(1).toBe(1);",
        "test('outro', async () => {});\nawait page.goto('/');\nexpect(1).toBe(1);",
        "await page.goto(process.env.URL);\nexpect(1).toBe(1);",
    ],
)
def test_construcoes_que_o_codigo_e_dono_sao_recusadas(corpo):
    """import, require, wrapper de teste e env são montados por código."""
    assert validar_corpo(corpo) is not None


def test_teste_que_nao_roda_e_recusado():
    corpo = "test.skip();\nawait page.goto('/');\nexpect(1).toBe(1);"

    assert validar_corpo(corpo) is not None


def test_corpo_sem_interacao_com_a_pagina_e_recusado():
    """`expect(true).toBe(true)` é tão vazio escrito pelo QA quanto pelo coder."""
    motivo = validar_corpo("expect(true).toBe(true);")

    assert motivo is not None
    assert "página" in motivo


def test_corpo_sem_assercao_e_recusado():
    motivo = validar_corpo("await page.goto('/');")

    assert motivo is not None
    assert "afirma" in motivo


@pytest.mark.parametrize("corpo", ["", "   ", "\n"])
def test_corpo_vazio_e_recusado(corpo):
    assert validar_corpo(corpo) is not None


# ---------------------------------------------------------------------------
# montar_spec — o arquivo em volta do corpo
# ---------------------------------------------------------------------------


def test_spec_embute_a_url_como_constante():
    """A URL vai assada no arquivo: o runner não repassa variáveis novas."""
    conteudo, _ = montar_spec(
        [TesteDeCriterio(criterion_id="CA-01", titulo="lista álbuns", corpo=_CORPO_OK)],
        "http://localhost:8000",
    )

    assert "const BASE_URL = 'http://localhost:8000';" in conteudo
    assert "import { test, expect } from '@playwright/test';" in conteudo
    assert conteudo.count("test('") == 1


def test_titulo_carrega_o_id_do_criterio():
    """É o título que reidentifica o critério no relatório do Playwright."""
    conteudo, titulos = montar_spec(
        [TesteDeCriterio(criterion_id="CA-02", titulo="cria ensaio", corpo=_CORPO_OK)],
        "http://localhost:8000",
    )

    assert titulos == {"CA-02": "CA-02 :: cria ensaio"}
    assert "CA-02 :: cria ensaio" in conteudo


def test_aspas_no_titulo_nao_quebram_o_literal():
    titulo = titulo_do_teste("CA-01", "exibe o botão 'Novo álbum'")
    conteudo, _ = montar_spec(
        [TesteDeCriterio(criterion_id="CA-01", titulo=titulo, corpo=_CORPO_OK)],
        "http://localhost:8000",
    )

    # A aspa simples precisa estar escapada dentro do literal TypeScript.
    assert "\\'Novo álbum\\'" in conteudo


# ---------------------------------------------------------------------------
# status_por_titulo — leitura do relatório bruto
# ---------------------------------------------------------------------------


def _relatorio(*pares: tuple[str, str]) -> dict:
    return {
        "suites": [
            {
                "title": "criterios.spec.ts",
                "specs": [
                    {"title": titulo, "tests": [{"status": status}]}
                    for titulo, status in pares
                ],
            }
        ]
    }


def test_le_status_por_teste_em_suites_aninhadas():
    relatorio = {
        "suites": [
            {"suites": [_relatorio(("CA-01 :: a", "expected"))["suites"][0]]},
        ]
    }

    assert status_por_titulo(relatorio) == {"CA-01 :: a": "expected"}


def test_pior_status_prevalece_para_o_mesmo_titulo():
    """Comprovação exige que TODAS as execuções tenham passado."""
    relatorio = {
        "suites": [
            {
                "specs": [
                    {
                        "title": "CA-01 :: a",
                        "tests": [{"status": "expected"}, {"status": "unexpected"}],
                    }
                ]
            }
        ]
    }

    assert status_por_titulo(relatorio) == {"CA-01 :: a": "unexpected"}


@pytest.mark.parametrize("entrada", [None, {}, [], "texto", 42])
def test_relatorio_invalido_nao_estoura(entrada):
    assert status_por_titulo(entrada) == {}


# ---------------------------------------------------------------------------
# montar_evidencias — tradução para o vocabulário do harness
# ---------------------------------------------------------------------------


_AUSENTE = object()


def _evidencias_para(status_por_teste: dict[str, str], **kwargs):
    """Helper com defaults por SENTINELA, não por `or`.

    `titulos={}` é um caso legítimo e distinto de "não informei" — com `or` os
    dois colapsariam no default e os testes de recusa passariam pelo caminho
    errado sem que nada acusasse.
    """
    titulos = kwargs.pop("titulos", _AUSENTE)
    return montar_evidencias(
        kwargs.pop("criterios", None) or _criterios("CA-01"),
        kwargs.pop("especificacao", None) or EspecificacaoCriterios(),
        {"CA-01": "CA-01 :: a"} if titulos is _AUSENTE else titulos,
        status_por_teste,
        kwargs.pop("recusas", None) or {},
        "http://localhost:8000",
    )


def test_teste_que_passou_vira_atendido():
    (evidencia,) = _evidencias_para({"CA-01 :: a": "expected"})

    assert evidencia.outcome is CriterionOutcome.ATENDIDO
    assert evidencia.checkable is True
    assert evidencia.criterion_id == "CA-01"


@pytest.mark.parametrize("status", ["unexpected", "flaky"])
def test_teste_que_falhou_ou_oscila_vira_nao_atendido(status):
    """`flaky` conta como falha: prova instável não é prova."""
    (evidencia,) = _evidencias_para({"CA-01 :: a": status})

    assert evidencia.outcome is CriterionOutcome.NAO_ATENDIDO


def test_teste_pulado_nunca_vira_reprovacao():
    """Ausência de execução não é evidência de ausência do comportamento."""
    (evidencia,) = _evidencias_para({"CA-01 :: a": "skipped"})

    assert evidencia.outcome is CriterionOutcome.TESTE_NAO_EXECUTADO
    assert evidencia.checkable is False


def test_corpo_recusado_vira_lacuna_enderecavel():
    (evidencia,) = _evidencias_para(
        {}, titulos={}, recusas={"CA-01": "não afirma nada"}
    )

    assert evidencia.outcome is CriterionOutcome.SEM_TESTE_MAPEADO
    assert "não afirma nada" in evidencia.observed


def test_criterio_declarado_fora_de_alcance_vira_nao_automatizavel():
    """Limite da ferramenta nunca é cobrado do coder."""
    especificacao = EspecificacaoCriterios(
        nao_verificaveis=[
            CriterioNaoVerificavel(criterion_id="CA-01", motivo="julgamento estético")
        ]
    )

    (evidencia,) = _evidencias_para({}, titulos={}, especificacao=especificacao)

    assert evidencia.outcome is CriterionOutcome.NAO_AUTOMATIZAVEL


def test_toda_a_task_aparece_na_evidencia():
    """O denominador precisa ser o mesmo que seria sem QA nenhum."""
    evidencias = _evidencias_para(
        {"CA-01 :: a": "expected"}, criterios=_criterios("CA-01", "CA-02", "CA-03")
    )

    assert [e.criterion_id for e in evidencias] == ["CA-01", "CA-02", "CA-03"]


# ---------------------------------------------------------------------------
# _filtrar_testes — o coder (e o QA) não inventam critérios
# ---------------------------------------------------------------------------


def test_id_inexistente_na_task_e_descartado():
    """Mesma regra do mapa do coder: id inventado não vira cobertura."""
    especificacao = EspecificacaoCriterios(
        testes=[TesteDeCriterio(criterion_id="CA-99", titulo="x", corpo=_CORPO_OK)]
    )

    aprovados, recusas = _filtrar_testes(especificacao, _criterios("CA-01"))

    assert aprovados == []
    assert recusas == {}


def test_id_em_grafia_diferente_e_canonizado():
    especificacao = EspecificacaoCriterios(
        testes=[TesteDeCriterio(criterion_id="ca-1", titulo="x", corpo=_CORPO_OK)]
    )

    aprovados, _ = _filtrar_testes(especificacao, _criterios("CA-01"))

    assert [t.criterion_id for t in aprovados] == ["CA-01"]


def test_id_repetido_mantem_apenas_o_primeiro():
    """Dois testes para o mesmo critério colidiriam no mapa título ↔ critério."""
    especificacao = EspecificacaoCriterios(
        testes=[
            TesteDeCriterio(criterion_id="CA-01", titulo="primeiro", corpo=_CORPO_OK),
            TesteDeCriterio(criterion_id="CA-01", titulo="segundo", corpo=_CORPO_OK),
        ]
    )

    aprovados, _ = _filtrar_testes(especificacao, _criterios("CA-01"))

    assert [t.titulo for t in aprovados] == ["primeiro"]


def test_corpo_recusado_e_registrado_como_recusa():
    especificacao = EspecificacaoCriterios(
        testes=[
            TesteDeCriterio(
                criterion_id="CA-01", titulo="x", corpo="expect(true).toBe(true);"
            )
        ]
    )

    aprovados, recusas = _filtrar_testes(especificacao, _criterios("CA-01"))

    assert aprovados == []
    assert "CA-01" in recusas


# ---------------------------------------------------------------------------
# base_tecnica_comprovada — o portão de entrada do QA
# ---------------------------------------------------------------------------


def _report(implantacao: str, inicializacao: str) -> dict:
    return {
        "stages": [
            {"stage": "implantacao_artefato", "status": implantacao},
            {"stage": "inicializacao_aplicacao", "status": inicializacao},
        ]
    }


def test_portao_abre_com_build_e_app_no_ar():
    assert base_tecnica_comprovada(_report("sucesso", "sucesso")) is True


@pytest.mark.parametrize(
    "implantacao,inicializacao",
    [("falha", "sucesso"), ("sucesso", "falha"), ("sucesso", "pulado")],
)
def test_portao_fecha_sem_base_tecnica(implantacao, inicializacao):
    """`pulado` na inicialização é justamente o artefato sem interface."""
    assert base_tecnica_comprovada(_report(implantacao, inicializacao)) is False


@pytest.mark.parametrize("entrada", [None, {}, "texto", 42, {"stages": []}])
def test_portao_fecha_para_report_inutilizavel(entrada):
    assert base_tecnica_comprovada(entrada) is False


# ---------------------------------------------------------------------------
# Furos do portão — casos que ATACAM a implementação, não a espelham
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "corpo,descricao",
    [
        (
            "await page.context().route('**/api', r => r.fulfill({body:'[]'}));\n"
            "await page.goto('/');\nawait expect(page.locator('h1')).toBeVisible();",
            "route via page.context()",
        ),
        (
            "await page.routeFromHAR('x.har');\nawait page.goto('/');\n"
            "await expect(page.locator('h1')).toBeVisible();",
            "routeFromHAR",
        ),
        (
            "const p = page;\nawait p.route('**/api', r => r.abort());\n"
            "await page.goto('/');\nawait expect(page.locator('h1')).toBeVisible();",
            "route via alias",
        ),
        (
            "await page['route']('**/api', r => r.abort());\nawait page.goto('/');\n"
            "await expect(page.locator('h1')).toBeVisible();",
            "route por indexação",
        ),
        (
            "await page.goto('/');\n"
            "await page.evaluate(() => document.body.innerHTML = '<h1>Álbuns</h1>');\n"
            "await expect(page.locator('h1')).toBeVisible();",
            "evaluate reescrevendo o DOM",
        ),
        (
            "await page.addInitScript(() => window.fetch = async () => new Response('[]'));\n"
            "await page.goto('/');\nawait expect(page.locator('h1')).toBeVisible();",
            "addInitScript",
        ),
    ],
)
def test_formas_alternativas_de_forjar_a_aplicacao_sao_recusadas(corpo, descricao):
    """Restringir a proibição a `page.route` deixava todas estas passarem."""
    assert validar_corpo(corpo) is not None, f"passou no portão: {descricao}"


def test_corpo_todo_comentado_nao_passa():
    """O furo mais barato: satisfazer os regexes dentro de um comentário."""
    corpo = (
        "// await page.goto('/');\n// await expect(page.locator('h1')).toBeVisible();"
    )

    assert validar_corpo(corpo) is not None


def test_interacao_e_assercao_dentro_de_comentario_nao_contam():
    corpo = "/* page.goto('/') e expect( */\nconst x = 1;"

    assert validar_corpo(corpo) is not None


def test_page_em_string_nao_conta_como_interacao():
    corpo = "const s = 'page.goto e expect(';\nconsole.log(s);"

    assert validar_corpo(corpo) is not None


def test_navegacao_para_fora_da_aplicacao_e_recusada():
    """`test.use({baseURL})` só resolve caminho relativo; URL absoluta escapa."""
    corpo = (
        "await page.goto('https://example.com');\n"
        "await expect(page.locator('h1')).toBeVisible();"
    )

    motivo = validar_corpo(corpo)

    assert motivo is not None
    assert "absoluta" in motivo


def test_import_dinamico_e_recusado():
    corpo = (
        "const fs = await import('fs');\nawait page.goto('/');\n"
        "await expect(page.locator('h1')).toBeVisible();"
    )

    assert validar_corpo(corpo) is not None


def test_comentario_ao_lado_de_codigo_valido_nao_atrapalha():
    """A limpeza não pode recusar um corpo legítimo que só tem comentário."""
    corpo = (
        "// verifica o cabeçalho do álbum\n"
        "await page.goto('/albuns');\n"
        "await expect(page.getByRole('heading', { name: 'Álbuns' })).toBeVisible();"
    )

    assert validar_corpo(corpo) is None


# ---------------------------------------------------------------------------
# Consolidação de status repetido — severidade, não ordem de chegada
# ---------------------------------------------------------------------------


def test_falha_prevalece_sobre_pulado_em_qualquer_ordem():
    """Antes só `expected` era sobrescrito: `skipped` mascarava uma falha real."""

    def _rel(*status):
        return {
            "suites": [
                {
                    "specs": [
                        {
                            "title": "CA-01 :: a",
                            "tests": [{"status": s} for s in status],
                        }
                    ]
                }
            ]
        }

    assert status_por_titulo(_rel("skipped", "unexpected")) == {
        "CA-01 :: a": "unexpected"
    }
    assert status_por_titulo(_rel("unexpected", "skipped")) == {
        "CA-01 :: a": "unexpected"
    }
    assert status_por_titulo(_rel("expected", "skipped")) == {"CA-01 :: a": "skipped"}


def test_status_interrompido_nao_vira_reprovacao():
    """Suíte cortada por timeout emite `interrupted` — não é falha da entrega."""
    (evidencia,) = _evidencias_para({"CA-01 :: a": "interrupted"})

    assert evidencia.outcome is CriterionOutcome.TESTE_NAO_EXECUTADO


# ---------------------------------------------------------------------------
# Furos fechados na 2ª rodada de revisão
# ---------------------------------------------------------------------------


def test_literal_de_regex_nao_esconde_codigo_do_portao():
    """Um `/[/*]/` engana qualquer limpador de comentários ingênuo.

    Era o furo mais sério do portão: o `/*` dentro do literal fazia o limpador
    apagar como "comentário de bloco" o `page.route(...)` que vinha depois, e a
    interceptação de rede atravessava inteira.
    """
    corpo = (
        "const a = /[/*]/;\n"
        "await page.route(/.*api.*/, x => x.abort());\n"
        "const b = /[*/]/;\n"
        "await page.goto('/');\n"
        "await expect(page.locator('h1')).toBeVisible();"
    )

    assert validar_corpo(corpo) is not None


@pytest.mark.parametrize(
    "chamada",
    [
        "await page.$eval('body', el => el.innerHTML = '<h1>ok</h1>');",
        "await page.$$eval('li', els => els.length);",
        "await page.exposeFunction('f', () => 1);",
        "await page.waitForFunction(() => { document.title = 'ok'; return true; });",
    ],
)
def test_primos_de_evaluate_tambem_sao_recusados(chamada):
    """`$eval` faz o que `evaluate` faz — bloquear um só seria arbitrário."""
    corpo = f"{chamada}\nawait page.goto('/');\nawait expect(page.locator('h1')).toBeVisible();"

    assert validar_corpo(corpo) is not None


@pytest.mark.parametrize(
    "acesso",
    [
        "page['ro' + 'ute']('**/api', r => r.abort());",
        "const m = 'route';\npage[m]('**/api', r => r.abort());",
        "page['\\u0072oute']('**/api', r => r.abort());",
    ],
)
def test_acesso_computado_e_recusado_como_construcao(acesso):
    """Nenhuma lista de nomes alcança um método montado em tempo de execução.

    Por isso a CONSTRUÇÃO inteira é recusada, e não os nomes um a um.
    """
    corpo = f"{acesso}\nawait page.goto('/');\nawait expect(page.locator('h1')).toBeVisible();"

    assert validar_corpo(corpo) is not None


def test_url_absoluta_em_variavel_tambem_e_recusada():
    """Checar só o argumento literal de `goto` deixava a variável passar."""
    corpo = (
        "const u = 'https://example.com';\n"
        "await page.goto(u);\n"
        "await expect(page.locator('h1')).toBeVisible();"
    )

    assert validar_corpo(corpo) is not None


def test_localizador_com_regex_continua_valendo():
    """`getByRole({ name: /álbum/i })` é idiomático — não pode ser recusado."""
    corpo = (
        "await page.goto('/albuns');\n"
        "await expect(page.getByRole('heading', { name: /álbum/i })).toBeVisible();"
    )

    assert validar_corpo(corpo) is None


# ---------------------------------------------------------------------------
# Reuso de spec — o que sustenta a reprodutibilidade da nota
# ---------------------------------------------------------------------------


def _spec_de_exemplo(destino, task_id="TASK-001", chave="k1"):
    from src.agents.workflow_coding_review.executor.qa_criterios.spec import (
        escrever_spec,
        montar_spec,
    )

    testes = [TesteDeCriterio(criterion_id="CA-01", titulo="lista", corpo=_CORPO_OK)]
    especificacao = EspecificacaoCriterios(testes=testes)
    conteudo, titulos = montar_spec(testes, "http://localhost:8000")
    caminho = escrever_spec(
        destino, task_id, conteudo, chave, especificacao, {}, titulos
    )
    return caminho, titulos


def test_spec_guardado_e_reusado_com_a_mesma_chave(tmp_path):
    _spec_de_exemplo(tmp_path)

    guardado = _ler_spec_guardado(tmp_path, "TASK-001", "k1")

    assert guardado is not None
    _, testes, _, titulos, caminho = guardado
    assert [t.criterion_id for t in testes] == ["CA-01"]
    assert titulos == {"CA-01": "CA-01 :: lista"}
    assert caminho.is_file()


def test_chave_diferente_nao_reusa(tmp_path):
    """Código ou critérios mudaram: o spec anterior pode não valer mais."""
    _spec_de_exemplo(tmp_path)

    assert _ler_spec_guardado(tmp_path, "TASK-001", "outra-chave") is None


def test_spec_dessincronizado_do_meta_nao_e_reusado(tmp_path):
    """As duas escritas não são atômicas entre si.

    Reusar os títulos do meta VELHO com um spec NOVO faria nenhum teste casar, e
    todo critério viraria `TESTE_NAO_EXECUTADO` — o degrau sairia da nota em
    silêncio, sem nada indicando que houve um problema de escrita.
    """
    caminho, _ = _spec_de_exemplo(tmp_path)
    caminho.write_text("// outro conteúdo qualquer\n", encoding="utf-8")

    assert _ler_spec_guardado(tmp_path, "TASK-001", "k1") is None


def test_sem_chave_o_meta_e_removido(tmp_path):
    """Identidade indeterminada: nada é reusável, e o meta velho não pode ficar.

    Um meta velho ao lado de um spec novo é pior que meta nenhum — a rodada
    seguinte casaria títulos que não existem no arquivo.
    """
    _spec_de_exemplo(tmp_path)
    assert (tmp_path / "criterios_TASK-001.meta.json").is_file()

    from src.agents.workflow_coding_review.executor.qa_criterios.spec import (
        escrever_spec,
    )

    escrever_spec(
        tmp_path, "TASK-001", "// novo\n", None, EspecificacaoCriterios(), {}, {}
    )

    assert not (tmp_path / "criterios_TASK-001.meta.json").exists()
    assert _ler_spec_guardado(tmp_path, "TASK-001", "k1") is None


def test_meta_ausente_ou_corrompido_nao_estoura(tmp_path):
    assert _ler_spec_guardado(tmp_path, "TASK-001", "k1") is None
    (tmp_path / "criterios_TASK-001.meta.json").write_text("{lixo", encoding="utf-8")
    assert _ler_spec_guardado(tmp_path, "TASK-001", "k1") is None


def test_chave_de_reuso_muda_com_criterios_e_url(tmp_path):
    """A chave precisa cobrir tudo que muda o spec correto."""
    (tmp_path / "app.py").write_text("print(1)", encoding="utf-8")
    base = _chave_de_reuso(_criterios("CA-01"), tmp_path, "http://localhost:8000")

    assert base == _chave_de_reuso(
        _criterios("CA-01"), tmp_path, "http://localhost:8000"
    )
    assert base != _chave_de_reuso(
        _criterios("CA-02"), tmp_path, "http://localhost:8000"
    )
    assert base != _chave_de_reuso(
        _criterios("CA-01"), tmp_path, "http://localhost:9000"
    )

    # Código alterado ⇒ chave nova: os localizadores podem ter mudado junto.
    (tmp_path / "app.py").write_text("print(2)", encoding="utf-8")
    assert base != _chave_de_reuso(
        _criterios("CA-01"), tmp_path, "http://localhost:8000"
    )


def test_sem_fingerprint_nao_ha_chave(monkeypatch, tmp_path):
    """Sem identidade não se reusa NEM se guarda — ver `escrever_spec`."""
    import src.agents.workflow_coding_review.executor.qa_criterios.verificacao as mod

    def _explode(_):
        raise OSError("disco fora")

    monkeypatch.setattr(mod, "fingerprint_workspace", _explode)

    assert _chave_de_reuso(_criterios("CA-01"), tmp_path, "http://x:8000") is None
