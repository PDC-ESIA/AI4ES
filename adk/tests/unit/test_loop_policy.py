"""Testes da política de continuidade do loop (issue #394).

Esta política decide quando o loop `coder ↔ executor` para. Os dois erros
possíveis não são simétricos:

- parar cedo demais → corta uma entrega que ainda estava evoluindo, que é
  justamente a queixa contra o teto fixo de 5 iterações;
- parar tarde demais → queima iterações reproduzindo a mesma falha.

O primeiro é o mais grave, e é por isso que os gatilhos "sem alteração de
arquivos" e "erro repetido" NÃO param o loop sozinhos: exigem também ausência
de melhora na nota. Vários testes aqui existem só para travar esse contrato.
"""

import pytest

from src.agents.workflow_coding_review.executor import loop_policy
from src.agents.workflow_coding_review.executor.loop_policy import (
    CHAVES_DE_CICLO,
    MOTIVO_ERRO_REPETIDO,
    MOTIVO_PLATO,
    MOTIVO_SEM_ALTERACAO,
    assinatura_erro,
    avaliar_continuidade,
    contar_rodadas_sem_progresso,
    fingerprint_mudou,
    registrar_e_avaliar,
)

_JANELA = 3
_MARGEM = 0.01


def _avaliar(
    historico, *, mudaram=True, atual=None, anterior=None, janela=_JANELA, acelerar=2
):
    return avaliar_continuidade(
        historico_notas=historico,
        arquivos_mudaram=mudaram,
        assinatura_erro_atual=atual,
        assinatura_erro_anterior=anterior,
        janela_sem_progresso=janela,
        margem_melhora=_MARGEM,
        rodadas_para_acelerar=acelerar,
    )


# ---------------------------------------------------------------------------
# contar_rodadas_sem_progresso — a contagem que caracteriza platô
# ---------------------------------------------------------------------------


def test_historico_vazio_nao_tem_rodada_sem_progresso():
    assert contar_rodadas_sem_progresso([], _MARGEM) == 0


def test_primeira_rodada_nunca_conta_como_sem_progresso():
    """Não há recorde anterior a superar; contar como platô puniria a estreia."""
    assert contar_rodadas_sem_progresso([0.0], _MARGEM) == 0


def test_progresso_continuo_zera_a_contagem():
    assert contar_rodadas_sem_progresso([0.1, 0.3, 0.6, 0.9], _MARGEM) == 0


def test_nota_estavel_acumula_rodadas_sem_progresso():
    assert contar_rodadas_sem_progresso([0.4, 0.4, 0.4, 0.4], _MARGEM) == 3


def test_vale_temporario_e_absorvido_quando_o_recorde_e_superado():
    """O caso central da issue: a nota cai e volta a subir.

    Uma correção que conserta A e quebra B derruba a nota por uma rodada. Como a
    comparação é contra o RECORDE (não contra a rodada anterior), o vale consome
    tolerância mas o avanço posterior renova a janela.
    """
    assert contar_rodadas_sem_progresso([0.50, 0.42, 0.48, 0.53], _MARGEM) == 0


def test_vale_sem_recuperacao_continua_contando():
    """Cair e estabilizar abaixo do recorde é platô, não avanço."""
    assert contar_rodadas_sem_progresso([0.50, 0.42, 0.44, 0.43], _MARGEM) == 3


def test_melhora_menor_que_a_margem_nao_conta_como_progresso():
    assert contar_rodadas_sem_progresso([0.50, 0.5001, 0.5002], _MARGEM) == 2


# ---------------------------------------------------------------------------
# Gatilho 1 — platô (único autônomo)
# ---------------------------------------------------------------------------


def test_plato_encerra_o_loop():
    decisao = _avaliar([0.4, 0.4, 0.4, 0.4])

    assert decisao.parar
    assert decisao.motivo == MOTIVO_PLATO


def test_abaixo_da_janela_o_loop_continua():
    decisao = _avaliar([0.4, 0.4, 0.4])

    assert not decisao.parar


def test_progresso_continuo_nunca_para():
    """Mais de 5 rodadas seguem enquanto houver avanço — o ponto da issue."""
    historico = []
    for nota in [0.1, 0.2, 0.35, 0.5, 0.62, 0.74, 0.88, 0.96]:
        historico.append(nota)
        assert not _avaliar(historico).parar


def test_vale_temporario_nao_encerra_por_engano():
    """Regressão direta do critério de aceite sobre queda temporária."""
    assert not _avaliar([0.50, 0.42, 0.48, 0.53]).parar


# ---------------------------------------------------------------------------
# Gatilho 2 — sem alteração de arquivos (nunca sozinho)
# ---------------------------------------------------------------------------


def test_sem_alteracao_com_nota_parada_encerra():
    decisao = _avaliar([0.4, 0.4, 0.4], mudaram=False)

    assert decisao.parar
    assert decisao.motivo == MOTIVO_SEM_ALTERACAO


def test_sem_alteracao_com_nota_subindo_nao_encerra():
    """Regressão: este gatilho já parou o loop sozinho numa versão da spec.

    A nota pode subir sem o workspace mudar — o validador julga critérios via
    LLM e testes podem ser instáveis. Encerrar aqui cortaria um avanço real.
    """
    decisao = _avaliar([0.4, 0.7], mudaram=False)

    assert not decisao.parar


def test_sem_alteracao_encerra_antes_da_janela_de_plato():
    """O valor do gatilho: acelera o platô em vez de esperar a janela inteira."""
    historico = [0.4, 0.4, 0.4]

    assert _avaliar(historico, mudaram=False).parar
    assert not _avaliar(historico, mudaram=True).parar


# ---------------------------------------------------------------------------
# Gatilho 3 — erro repetido (nunca sozinho)
# ---------------------------------------------------------------------------


def test_erro_repetido_com_nota_parada_encerra():
    decisao = _avaliar([0.4, 0.4, 0.4], atual="abc", anterior="abc")

    assert decisao.parar
    assert decisao.motivo == MOTIVO_ERRO_REPETIDO


def test_erro_repetido_com_nota_subindo_nao_encerra():
    """Regressão: mesma assinatura com nota melhor é progresso, não travamento."""
    decisao = _avaliar([0.4, 0.7], atual="abc", anterior="abc")

    assert not decisao.parar


def test_assinatura_diferente_nao_encerra():
    decisao = _avaliar([0.4, 0.4, 0.4], atual="abc", anterior="xyz")

    assert not decisao.parar


def test_sem_assinatura_o_gatilho_nao_dispara():
    """Rodada recusada pelo gate não tem ExecutionReport — nada a comparar."""
    decisao = _avaliar([0.4, 0.4, 0.4], atual=None, anterior=None)

    assert not decisao.parar


def test_erro_repetido_cobre_o_coder_que_edita_sem_progredir():
    """Complementa o gatilho 2: arquivos MUDAM, mas a falha é a mesma."""
    decisao = _avaliar([0.4, 0.4, 0.4], mudaram=True, atual="abc", anterior="abc")

    assert decisao.parar
    assert decisao.motivo == MOTIVO_ERRO_REPETIDO


# ---------------------------------------------------------------------------
# assinatura_erro — fina o bastante para não confundir avanço com repetição
# ---------------------------------------------------------------------------


def _report_com_testes(passaram: int, falharam: int) -> dict:
    return {
        "stages": [
            {
                "stage": "testes_automatizados",
                "status": "falha",
                "error_code": "TESTES_FALHARAM",
                "evidence": {
                    "resultados": [
                        {
                            "resumo": {
                                "passaram": passaram,
                                "falharam": falharam,
                                "erros": 0,
                            }
                        }
                    ]
                },
            }
        ]
    }


_VEREDITO_GENERICO = {
    "blocking_reason": "Ao menos um critério ficou nao_atendido ou inconclusivo.",
    "criteria_verdicts": [
        {"criterion": "CA-1", "status": "nao_atendido", "reasoning": "x"}
    ],
}


def test_mesma_falha_com_menos_testes_quebrados_muda_a_assinatura():
    """Regressão do bug encontrado na revisão da spec.

    `error_code` e `blocking_reason` são idênticos entre as duas rodadas — o
    `blocking_reason` da Camada 2 é uma string fixa. Só a contagem de testes
    distingue 10/30 de 28/30; sem ela o loop pararia no meio do avanço.
    """
    antes = assinatura_erro(_report_com_testes(10, 20), _VEREDITO_GENERICO)
    depois = assinatura_erro(_report_com_testes(28, 2), _VEREDITO_GENERICO)

    assert antes != depois


def test_falha_identica_repete_a_assinatura():
    a = assinatura_erro(_report_com_testes(10, 20), _VEREDITO_GENERICO)
    b = assinatura_erro(_report_com_testes(10, 20), _VEREDITO_GENERICO)

    assert a == b


def test_reasoning_do_llm_nao_entra_na_assinatura():
    """Texto livre muda de redação sem o resultado mudar; incluí-lo desligaria
    o gatilho na prática, porque a assinatura nunca repetiria."""
    outro_texto = {
        "blocking_reason": _VEREDITO_GENERICO["blocking_reason"],
        "criteria_verdicts": [
            {
                "criterion": "CA-1",
                "status": "nao_atendido",
                "reasoning": "redacao completamente diferente desta vez",
            }
        ],
    }

    assert assinatura_erro(
        _report_com_testes(10, 20), _VEREDITO_GENERICO
    ) == assinatura_erro(_report_com_testes(10, 20), outro_texto)


def test_mudanca_de_status_de_criterio_muda_a_assinatura():
    atendido = {
        "criteria_verdicts": [
            {"criterion": "CA-1", "status": "atendido", "reasoning": "x"}
        ]
    }

    assert assinatura_erro(
        _report_com_testes(10, 20), _VEREDITO_GENERICO
    ) != assinatura_erro(_report_com_testes(10, 20), atendido)


@pytest.mark.parametrize("entrada", [None, "", [], 42])
def test_assinatura_tolera_entradas_invalidas(entrada):
    assert isinstance(assinatura_erro(entrada, entrada), str)


# ---------------------------------------------------------------------------
# registrar_e_avaliar — o ponto único usado pelos dois callbacks
# ---------------------------------------------------------------------------


def test_registra_historico_e_detalhe_na_mesma_ordem():
    state: dict = {}

    registrar_e_avaliar(state, 0.3, {"build_concluido": 1.0}, arquivos_mudaram=True)
    registrar_e_avaliar(state, 0.6, {"build_concluido": 1.0}, arquivos_mudaram=True)

    assert state["progress_score_history"] == [0.3, 0.6]
    assert len(state["progress_score_details"]) == 2


def test_detalhe_ausente_e_registrado_como_none():
    """Caminho do gate estrutural: não há nota por degrau, mas a rodada conta."""
    state: dict = {}

    registrar_e_avaliar(state, 0.0, None, arquivos_mudaram=False)

    assert state["progress_score_history"] == [0.0]
    assert state["progress_score_details"] == [None]


def test_listas_sao_reatribuidas_e_nao_mutadas_no_lugar():
    """O state do callback rastreia delta por atribuição de chave; um `append`
    numa lista aninhada poderia não ser persistido fora da invocação."""
    state: dict = {}
    registrar_e_avaliar(state, 0.3, None, arquivos_mudaram=True)
    primeira = state["progress_score_history"]

    registrar_e_avaliar(state, 0.6, None, arquivos_mudaram=True)

    assert state["progress_score_history"] is not primeira


def test_recusas_seguidas_acabam_disparando_o_plato():
    """O gate estrutural registra 0.0 a cada recusa; sem avaliação, um coder
    travado antes do manifesto só pararia no teto de segurança."""
    state: dict = {}
    decisoes = [
        registrar_e_avaliar(state, 0.0, None, arquivos_mudaram=False) for _ in range(4)
    ]

    assert not decisoes[0].parar
    assert decisoes[-1].parar
    assert state["loop_stop_reason"] in {MOTIVO_PLATO, MOTIVO_SEM_ALTERACAO}


def test_motivo_de_parada_so_e_gravado_quando_para():
    state: dict = {}

    registrar_e_avaliar(state, 0.5, None, arquivos_mudaram=True)

    assert "loop_stop_reason" not in state


def test_assinatura_e_guardada_para_a_proxima_rodada():
    state: dict = {}

    registrar_e_avaliar(
        state, 0.5, None, arquivos_mudaram=True, assinatura_erro_atual="abc"
    )

    assert state["progress_last_error_signature"] == "abc"


def test_assinatura_ausente_nao_apaga_a_anterior():
    state = {"progress_last_error_signature": "abc"}

    registrar_e_avaliar(
        state, 0.5, None, arquivos_mudaram=True, assinatura_erro_atual=None
    )

    assert state["progress_last_error_signature"] == "abc"


# ---------------------------------------------------------------------------
# fingerprint_mudou
# ---------------------------------------------------------------------------


def test_primeira_rodada_conta_como_alterada(monkeypatch):
    """Sem rodada anterior não existe estagnação a declarar."""
    monkeypatch.setattr(loop_policy, "fingerprint_workspace", lambda _: "hash-a")
    monkeypatch.setattr(loop_policy, "get_agent_workspace", lambda _: "/tmp/ws")
    state: dict = {}

    assert fingerprint_mudou(state) is True
    assert state["progress_last_fingerprint"] == "hash-a"


def test_mesmo_fingerprint_indica_ausencia_de_alteracao(monkeypatch):
    monkeypatch.setattr(loop_policy, "fingerprint_workspace", lambda _: "hash-a")
    monkeypatch.setattr(loop_policy, "get_agent_workspace", lambda _: "/tmp/ws")
    state = {"progress_last_fingerprint": "hash-a"}

    assert fingerprint_mudou(state) is False


def test_fingerprint_diferente_indica_alteracao(monkeypatch):
    monkeypatch.setattr(loop_policy, "fingerprint_workspace", lambda _: "hash-b")
    monkeypatch.setattr(loop_policy, "get_agent_workspace", lambda _: "/tmp/ws")
    state = {"progress_last_fingerprint": "hash-a"}

    assert fingerprint_mudou(state) is True
    assert state["progress_last_fingerprint"] == "hash-b"


def test_falha_ao_medir_assume_alteracao(monkeypatch):
    """Conservador: uma medida auxiliar quebrada não pode encerrar a task."""

    def _explode(_):
        raise OSError("workspace inacessível")

    monkeypatch.setattr(loop_policy, "fingerprint_workspace", _explode)
    monkeypatch.setattr(loop_policy, "get_agent_workspace", lambda _: "/tmp/ws")

    assert fingerprint_mudou({}) is True


# ---------------------------------------------------------------------------
# Chaves de ciclo
# ---------------------------------------------------------------------------


def test_todas_as_chaves_escritas_estao_declaradas_para_limpeza():
    """Uma chave que escapasse da limpeza faria a task seguinte herdar o
    histórico da anterior e ser cortada antes da primeira tentativa real."""
    state: dict = {}
    registrar_e_avaliar(
        state, 0.0, None, arquivos_mudaram=False, assinatura_erro_atual="a"
    )
    registrar_e_avaliar(
        state, 0.0, None, arquivos_mudaram=False, assinatura_erro_atual="a"
    )
    registrar_e_avaliar(
        state, 0.0, None, arquivos_mudaram=False, assinatura_erro_atual="a"
    )
    registrar_e_avaliar(
        state, 0.0, None, arquivos_mudaram=False, assinatura_erro_atual="a"
    )

    assert set(state) <= set(CHAVES_DE_CICLO)
    assert "loop_stop_reason" in state  # o cenário realmente chegou a parar


# ---------------------------------------------------------------------------
# Regressão: o vale isolado não pode acionar os gatilhos aceleradores
# ---------------------------------------------------------------------------


def test_vale_isolado_sem_alteracao_nao_encerra():
    """O falso positivo mais caro que esta política já teve.

    A nota cai numa rodada (a correção que conserta A e quebra B), o coder por
    acaso não edita nada, e a task morria ali — mesmo quando a rodada seguinte
    voltaria a subir. A nota ter se movido SEM alteração de arquivo é, se alguma
    coisa, evidência de não-determinismo, não de travamento.
    """
    assert not _avaliar([0.50, 0.42], mudaram=False).parar


def test_vale_isolado_com_erro_repetido_nao_encerra():
    """Mesmo vale, pelo outro acelerador."""
    assert not _avaliar([0.50, 0.42], atual="sig", anterior="sig").parar


def test_recuperacao_apos_vale_sobrevive_aos_aceleradores():
    """A sequência-símbolo da issue (0.50 → 0.42 → 0.48 → 0.53), rodada a rodada.

    O vale vem de uma rodada em que o coder não editou nada — o caso que
    derrubava a task. Depois ele volta a trabalhar e a nota se recupera.

    LIMITE CONHECIDO E DELIBERADO: se o coder ficasse TRÊS rodadas seguidas sem
    editar nada, o acelerador encerraria na terceira, mesmo que a nota estivesse
    subindo. Isso é aceito porque o cenário se contradiz — sem alteração de
    código a nota não se recupera sozinha; e protegê-lo exigiria elevar
    `rodadas_para_acelerar` até a janela do platô, o que tornaria os
    aceleradores código morto.
    """
    assert not _avaliar([0.50, 0.42], mudaram=False).parar
    assert not _avaliar([0.50, 0.42, 0.48], mudaram=True).parar
    assert not _avaliar([0.50, 0.42, 0.48, 0.53], mudaram=True).parar


def test_ausencia_de_progresso_persistente_ainda_encerra():
    """A tolerância é para o tropeço isolado, não para o travamento real."""
    decisao = _avaliar([0.50, 0.42, 0.44], mudaram=False)

    assert decisao.parar
    assert decisao.motivo == MOTIVO_SEM_ALTERACAO


def test_aceleradores_continuam_disparando_antes_do_plato():
    """Se disparassem junto com o platô seriam código morto."""
    historico = [0.4, 0.4, 0.4]

    assert _avaliar(historico, mudaram=False, janela=5).parar
    assert not _avaliar(historico, mudaram=True, janela=5).parar


# ---------------------------------------------------------------------------
# Regressão: configuração inválida não pode derrubar o import
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("valor", ["nan", "inf", "-inf", "abc", "0", "-3", ""])
def test_config_inteiro_recusa_valores_inutilizaveis(monkeypatch, valor):
    """`nan`/`inf` passavam pela comparação de mínimo e estouravam no int()."""
    from src.agents.workflow_coding_review.executor.loop_policy import config_inteiro

    monkeypatch.setenv("AI4ES_TESTE_CONFIG", valor)

    assert config_inteiro("AI4ES_TESTE_CONFIG", 20, minimo=1) == 20


def test_config_inteiro_recusa_fracionario_em_vez_de_truncar(monkeypatch):
    """Truncar 3.9 para 3 entregaria um limite diferente do configurado."""
    from src.agents.workflow_coding_review.executor.loop_policy import config_inteiro

    monkeypatch.setenv("AI4ES_TESTE_CONFIG", "3.9")

    assert config_inteiro("AI4ES_TESTE_CONFIG", 20, minimo=1) == 20


def test_config_inteiro_aceita_valor_valido(monkeypatch):
    from src.agents.workflow_coding_review.executor.loop_policy import config_inteiro

    monkeypatch.setenv("AI4ES_TESTE_CONFIG", " 7 ")

    assert config_inteiro("AI4ES_TESTE_CONFIG", 20, minimo=1) == 7


@pytest.mark.parametrize("valor", ["nan", "inf", "-inf"])
def test_config_fracionario_recusa_nao_finitos(monkeypatch, valor):
    """Um `nan` desligaria a política em silêncio: toda comparação com ele é False."""
    from src.agents.workflow_coding_review.executor.loop_policy import _config

    monkeypatch.setenv("AI4ES_TESTE_CONFIG", valor)

    assert _config("AI4ES_TESTE_CONFIG", 0.01, minimo=0.0) == 0.01
