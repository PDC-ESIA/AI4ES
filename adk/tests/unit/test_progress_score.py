"""Testes da nota de progresso (issue #394).

A nota substitui o teto fixo de iterações como critério primário do loop
`coder ↔ executor`. Por isso os testes aqui cobrem menos o "caminho feliz" e
mais as formas de a nota MENTIR sobre o progresso — cada uma delas faria o loop
parar no meio de um avanço real ou insistir numa solução travada:

- degrau pulado por falha upstream não pode ter o peso redistribuído (inflaria
  a nota justamente na rodada que fracassou);
- testes precisam pontuar fracionado, senão a nota fica cega enquanto o coder
  conserta a suíte um teste por vez;
- stack de teste não-pytest não pode zerar um degrau que foi conquistado;
- nenhum degrau pode depender de julgamento do LLM — foi o que travou a nota em
  ~0.65 permanentemente enquanto existia o degrau `CRITERIOS_ATENDIDOS`.
"""

import pytest

from src.agents.workflow_coding_review.executor.progress_score import (
    Degrau,
    _PESOS_BASE,
    calcular_nota,
    graus_aplicaveis,
    redistribuir_pesos,
)

# ---------------------------------------------------------------------------
# Construtores de ExecutionReport sintéticos
# ---------------------------------------------------------------------------

_SUCESSO = "sucesso"
_FALHA = "falha"
_ERRO = "erro"
_PULADO = "pulado"


def _estagio(nome: str, status: str, evidence: dict | None = None) -> dict:
    return {
        "stage": nome,
        "status": status,
        "duration_seconds": 0.0,
        "summary": "",
        "evidence": evidence or {},
        "error_code": None if status == _SUCESSO else "X",
    }


def _resumo_testes(passaram: int, falharam: int = 0, erros: int = 0) -> dict:
    """Evidência do estágio 6 no formato REAL do harness.

    Os contadores ficam por comando em `resultados[*].resumo` — o harness não
    persiste um agregado. Se este formato mudar, este teste quebra junto, que é
    exatamente o ponto.
    """
    return {
        "resultados": [
            {
                "comando": "pytest",
                "exit_code": 0 if falharam == 0 and erros == 0 else 1,
                "timed_out": False,
                "resumo": {
                    "passaram": passaram,
                    "falharam": falharam,
                    "erros": erros,
                    "total": passaram + falharam + erros,
                },
                "saida_tail": "",
            }
        ],
        "saida_tail": "",
    }


def _report(
    *,
    surface: str = "service",
    test_commands: tuple[str, ...] = ("pytest",),
    preparacao: str = _SUCESSO,
    implantacao: str = _SUCESSO,
    inicializacao: str = _SUCESSO,
    testes: str = _SUCESSO,
    evidencia_testes: dict | None = None,
) -> dict:
    """ExecutionReport sintético; por padrão, tudo verde num projeto service."""
    evidencia_preparacao = (
        {"surface": surface, "test_commands": list(test_commands)}
        if preparacao == _SUCESSO
        else {}
    )
    if evidencia_testes is None:
        # Espelha o harness: um estágio `pulado`/falho não carrega contadores —
        # `_pulado()` emite evidência vazia. Dar contadores de suíte verde a um
        # estágio que nem rodou inflaria a nota de rodadas que fracassaram antes.
        evidencia_testes = _resumo_testes(10) if testes == _SUCESSO else {}
    return {
        "work_item_id": "TASK-001",
        "iteration": 1,
        "overall_status": _SUCESSO,
        "stages": [
            _estagio("preparacao_ambiente", preparacao, evidencia_preparacao),
            _estagio("implantacao_artefato", implantacao),
            _estagio("inicializacao_aplicacao", inicializacao),
            _estagio("testes_automatizados", testes, evidencia_testes),
        ],
    }


# ---------------------------------------------------------------------------
# A nota mede EXECUÇÃO — nada que dependa de julgamento do LLM
# ---------------------------------------------------------------------------


def test_nota_nao_recebe_veredito_do_validador():
    """Contrato de assinatura: `calcular_nota` só aceita o ExecutionReport.

    Enquanto o `ValidationVerdict` entrava no cálculo, o degrau
    `CRITERIOS_ATENDIDOS` (35% do peso) ficava travado em 0 — o validador não
    consegue COMPROVAR um critério de UI e devolvia `inconclusivo` rodada após
    rodada. A nota teto virava ~0.65 e nenhuma task jamais aprovava. Manter a
    porta fechada na assinatura impede que isso volte por descuido.
    """
    with pytest.raises(TypeError):
        calcular_nota(_report(), {"criteria_verdicts": []})


def test_nenhum_degrau_depende_de_julgamento_semantico():
    assert not any("criterio" in degrau.value for degrau in Degrau)


# ---------------------------------------------------------------------------
# graus_aplicaveis — vem do manifesto, nunca do resultado da execução
# ---------------------------------------------------------------------------


def test_minimo_para_rodar_aplica_a_qualquer_projeto():
    for surface in ("service", "command", "none"):
        assert Degrau.MINIMO_PARA_RODAR in graus_aplicaveis(surface, ["pytest"])


def test_surface_none_dispensa_o_degrau_de_inicializacao():
    """Biblioteca não 'inicia uma aplicação' — o degrau não se aplica."""
    aplicaveis = graus_aplicaveis("none", ["pytest"])

    assert Degrau.APP_INICIOU not in aplicaveis
    assert Degrau.BUILD_CONCLUIDO in aplicaveis


@pytest.mark.parametrize("surface", ["service", "command"])
def test_surface_com_topo_exige_o_degrau_de_inicializacao(surface):
    assert Degrau.APP_INICIOU in graus_aplicaveis(surface, ["pytest"])


def test_manifesto_sem_comandos_de_teste_dispensa_o_degrau_de_testes():
    assert Degrau.TESTES_PASSARAM not in graus_aplicaveis("service", [])


def test_surface_desconhecida_mantem_todos_os_degraus():
    """Sem saber o tipo do projeto, dispensar degrau inflaria a nota."""
    assert graus_aplicaveis(None, []) == frozenset(Degrau)


# ---------------------------------------------------------------------------
# redistribuir_pesos — o teto continua sendo 1.0 para qualquer projeto
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "surface,test_commands",
    [
        ("service", ["pytest"]),
        ("command", ["pytest"]),
        ("none", ["pytest"]),
        ("none", []),
        ("service", []),
    ],
)
def test_pesos_somam_um_em_qualquer_perfil(surface, test_commands):
    pesos = redistribuir_pesos(graus_aplicaveis(surface, test_commands))

    assert sum(pesos.values()) == pytest.approx(1.0)


def test_peso_de_degrau_dispensado_e_diluido_proporcionalmente():
    """Diluir proporcional preserva a importância relativa entre os que ficam."""
    todos = redistribuir_pesos(frozenset(Degrau))
    sem_app = redistribuir_pesos(frozenset(Degrau) - {Degrau.APP_INICIOU})

    # A razão entre dois degraus sobreviventes não muda com a redistribuição.
    razao_antes = todos[Degrau.TESTES_PASSARAM] / todos[Degrau.BUILD_CONCLUIDO]
    razao_depois = sem_app[Degrau.TESTES_PASSARAM] / sem_app[Degrau.BUILD_CONCLUIDO]
    assert razao_depois == pytest.approx(razao_antes)
    assert sum(sem_app.values()) == pytest.approx(1.0)


def test_um_unico_degrau_aplicavel_recebe_todo_o_peso():
    pesos = redistribuir_pesos({Degrau.TESTES_PASSARAM})

    assert pesos == {Degrau.TESTES_PASSARAM: pytest.approx(1.0)}


def test_nenhum_degrau_aplicavel_devolve_vazio_sem_estourar():
    assert redistribuir_pesos(frozenset()) == {}


def test_pesos_base_somam_um_com_todos_os_degraus():
    """Guarda contra alguém editar `_PESOS_BASE` e desbalancear a escada."""
    assert sum(_PESOS_BASE.values()) == pytest.approx(1.0)
    assert set(_PESOS_BASE) == set(Degrau)


def test_testes_passaram_e_o_degrau_de_maior_peso():
    """É o proxy mais direto de 'funciona' e o único fracionário.

    Ser o mais pesado é o que dá à `loop_policy` um sinal forte e contínuo na
    fase mais comum de iteração — consertar a suíte um teste por vez.
    """
    assert _PESOS_BASE[Degrau.TESTES_PASSARAM] == max(_PESOS_BASE.values())


# ---------------------------------------------------------------------------
# calcular_nota — extremos
# ---------------------------------------------------------------------------


def test_tudo_verde_da_nota_maxima():
    """O teto 1.0 precisa ser ALCANÇÁVEL — antes travava em ~0.65."""
    nota = calcular_nota(_report())

    assert nota.total == pytest.approx(1.0)


def test_report_vazio_da_nota_quase_zero():
    """Só `MINIMO_PARA_RODAR` pontua: chegar aqui já implica gate aprovado."""
    nota = calcular_nota({})

    assert nota.por_degrau[Degrau.MINIMO_PARA_RODAR] == 1.0
    assert nota.total == pytest.approx(_PESOS_BASE[Degrau.MINIMO_PARA_RODAR])


@pytest.mark.parametrize("entrada", [None, "", [], 42])
def test_entradas_invalidas_nao_estouram(entrada):
    """O chamador é um callback no meio do fluxo; derrubá-lo custaria a rodada."""
    nota = calcular_nota(entrada)

    assert 0.0 <= nota.total <= 1.0


def test_minimo_para_rodar_e_sempre_um_dentro_de_calcular_nota():
    """Comportamento esperado, não bug: quem registra a falha do degrau 1 é o
    gate `recusar_execucao_incompleta`, gravando 0.0 na rodada que ele recusa."""
    nota = calcular_nota(_report(preparacao=_ERRO))

    assert nota.por_degrau[Degrau.MINIMO_PARA_RODAR] == 1.0


# ---------------------------------------------------------------------------
# calcular_nota — a escada sobe degrau a degrau
# ---------------------------------------------------------------------------


def test_nota_cresce_conforme_a_escada_avanca():
    """A propriedade central: mais capacidade conquistada, nota maior."""
    so_preparou = calcular_nota(
        _report(implantacao=_FALHA, inicializacao=_PULADO, testes=_PULADO)
    )
    construiu = calcular_nota(_report(inicializacao=_FALHA, testes=_PULADO))
    subiu = calcular_nota(
        _report(testes=_FALHA, evidencia_testes=_resumo_testes(0, falharam=5))
    )
    tudo = calcular_nota(_report())

    assert so_preparou.total < construiu.total < subiu.total < tudo.total


def test_degrau_pulado_por_falha_upstream_nao_tem_peso_redistribuido():
    """O caso que quebraria a nota: `pulado` por cascata NÃO é 'não se aplica'.

    Um projeto service cujo deploy falhou pula a inicialização. Se isso fosse
    lido como 'não se aplica', o peso de APP_INICIOU seria diluído e a nota
    subiria — premiando a rodada que fracassou.
    """
    cascata = calcular_nota(
        _report(implantacao=_FALHA, inicializacao=_PULADO, testes=_PULADO)
    )

    assert Degrau.APP_INICIOU in cascata.degraus_aplicaveis
    assert cascata.por_degrau[Degrau.APP_INICIOU] == 0.0

    # Numa biblioteca (surface=none) o MESMO estágio pulado é dispensa legítima.
    biblioteca = calcular_nota(_report(surface="none", inicializacao=_PULADO))
    assert Degrau.APP_INICIOU not in biblioteca.degraus_aplicaveis
    assert biblioteca.total == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Degrau de testes — fracionário e portável entre stacks
# ---------------------------------------------------------------------------


def test_testes_pontuam_fracionado():
    """Sem isso a nota fica cega enquanto o coder conserta a suíte aos poucos."""
    poucos = calcular_nota(
        _report(testes=_FALHA, evidencia_testes=_resumo_testes(2, falharam=8))
    )
    quase = calcular_nota(
        _report(testes=_FALHA, evidencia_testes=_resumo_testes(8, falharam=2))
    )

    assert poucos.por_degrau[Degrau.TESTES_PASSARAM] == pytest.approx(0.2)
    assert quase.por_degrau[Degrau.TESTES_PASSARAM] == pytest.approx(0.8)
    assert quase.total > poucos.total


def test_contadores_somam_entre_multiplos_comandos_de_teste():
    """O harness registra um `resumo` POR COMANDO; o agregado é feito aqui."""
    evidencia = {
        "resultados": [
            {"resumo": {"passaram": 3, "falharam": 1, "erros": 0}},
            {"resumo": {"passaram": 5, "falharam": 0, "erros": 1}},
        ],
        "saida_tail": "",
    }

    nota = calcular_nota(_report(testes=_FALHA, evidencia_testes=evidencia))

    assert nota.por_degrau[Degrau.TESTES_PASSARAM] == pytest.approx(8 / 10)


def test_stack_nao_pytest_com_suite_verde_nao_e_zerada():
    """Regressão: Jest/Maven/Go não casam o regex do harness e vêm com total=0.

    O estágio está `sucesso` (exit code 0, que não depende de regex nenhum), logo
    o degrau foi conquistado — zerá-lo puniria o projeto por não ser Python.
    """
    sem_contadores = {
        "resultados": [{"resumo": {"passaram": 0, "falharam": 0, "erros": 0}}]
    }

    nota = calcular_nota(_report(testes=_SUCESSO, evidencia_testes=sem_contadores))

    assert nota.por_degrau[Degrau.TESTES_PASSARAM] == 1.0
    assert nota.total == pytest.approx(1.0)


def test_estagio_de_testes_falho_sem_contadores_vale_zero():
    """Contrapartida: sem contadores E sem sucesso, não há o que creditar."""
    nota = calcular_nota(_report(testes=_FALHA, evidencia_testes={"resultados": []}))

    assert nota.por_degrau[Degrau.TESTES_PASSARAM] == 0.0


def test_contadores_corrompidos_nao_estouram():
    evidencia = {"resultados": [{"resumo": {"passaram": "muitos", "falharam": None}}]}

    nota = calcular_nota(_report(testes=_FALHA, evidencia_testes=evidencia))

    assert nota.por_degrau[Degrau.TESTES_PASSARAM] == 0.0


# ---------------------------------------------------------------------------
# Detalhamento auditável
# ---------------------------------------------------------------------------


def test_detalhamento_cobre_exatamente_os_degraus_aplicaveis():
    nota = calcular_nota(_report(surface="none", test_commands=()))

    assert set(nota.por_degrau) == set(nota.degraus_aplicaveis)
    assert set(nota.pesos_efetivos) == set(nota.degraus_aplicaveis)


def test_como_dict_serializa_com_chaves_de_texto():
    """O detalhamento vai para o session state e precisa sobreviver a JSON."""
    detalhe = calcular_nota(_report()).como_dict()

    assert detalhe[Degrau.TESTES_PASSARAM.value] == 1.0
    assert all(isinstance(chave, str) for chave in detalhe)
