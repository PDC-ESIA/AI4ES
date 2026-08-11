"""Testes da compactação efêmera do contexto do coder por task."""

from google.adk.models.llm_request import LlmRequest
from google.genai import types

from src.agents.workflow_coding_review.cr_coder import (
    _compactar_historico_entre_tasks,
)


def _content(role: str, text: str) -> types.Content:
    return types.Content(role=role, parts=[types.Part(text=text)])


def test_compactacao_descarta_tasks_antigas_e_preserva_retry_da_atual():
    request = LlmRequest(
        contents=[
            _content("user", "contrato global antigo"),
            _content("model", "tool call e resposta da TASK-001"),
            _content(
                "user",
                "[AI4ES_TASK_CONTEXT_START]\n{\"task\": \"TASK-002\"}",
            ),
            _content("model", "alteração anterior da TASK-002"),
            _content("user", "ErrorReport da TASK-002"),
        ]
    )

    resposta = _compactar_historico_entre_tasks(object(), request)

    assert resposta is None
    assert [content.parts[0].text for content in request.contents] == [
        "[AI4ES_TASK_CONTEXT_START]\n{\"task\": \"TASK-002\"}",
        "alteração anterior da TASK-002",
        "ErrorReport da TASK-002",
    ]


def test_compactacao_nao_altera_request_sem_ancora():
    request = LlmRequest(contents=[_content("user", "fluxo sem TaskIterator")])

    _compactar_historico_entre_tasks(object(), request)

    assert request.contents[0].parts[0].text == "fluxo sem TaskIterator"
