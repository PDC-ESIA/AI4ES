"""Testes da função aguardar_aprovacao_humana (HITL tool do qa_pipeline).

A função em si é um stub — quando registrada como LongRunningFunctionTool,
o ADK pausa antes do corpo executar. Os testes garantem:
  1. Assinatura compatível com Gemini schema (sem `str | None`).
  2. Retorno tipado com as chaves contratuais.
  3. Comportamento determinístico em chamada direta (importante para
     testes integration que invocam sem passar pelo runner).
"""

import inspect

import pytest


@pytest.mark.asyncio
async def test_aguardar_aprovacao_humana_retorna_dict_com_chaves_contratuais():
    from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana

    resultado = await aguardar_aprovacao_humana(
        checkpoint_id="abc",
        approval_question="Você aprova?",
        allowed_decisions=["aprovar", "rejeitar"],
        pause_reason="motivo",
    )

    assert isinstance(resultado, dict)
    for key in (
        "decision", "comments", "reviewer", "validated_at",
        "checkpoint_id", "approval_question",
        "allowed_decisions", "pause_reason",
    ):
        assert key in resultado, f"chave ausente: {key}"

    assert resultado["checkpoint_id"] == "abc"
    assert resultado["allowed_decisions"] == ["aprovar", "rejeitar"]


def test_aguardar_aprovacao_humana_assinatura_sem_union_pipe():
    """Gemini API rejeita anyOf gerado por `str | None`. Use Optional[str]."""
    from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana

    sig = inspect.signature(aguardar_aprovacao_humana)
    ann = sig.parameters["pause_reason"].annotation
    import types as _types
    assert not isinstance(ann, _types.UnionType), (
        f"pause_reason usa `str | None` (UnionType), rejeitado pelo Gemini. "
        f"Troque por Optional[str]. Got: {ann}"
    )


@pytest.mark.asyncio
async def test_pause_reason_pode_ser_omitido():
    from src.agents.qa_agent.tools.hitl_tool import aguardar_aprovacao_humana

    resultado = await aguardar_aprovacao_humana(
        checkpoint_id="x",
        approval_question="?",
        allowed_decisions=["aprovar"],
    )
    assert resultado["pause_reason"] is None
