"""Testes unitários para shared.callbacks.taco_validation.

Valida extração de JSON, normalização de campos com aliases,
validação contra schemas Pydantic e comportamento em cenários de erro.
"""

import json

import pytest
from unittest.mock import MagicMock

from shared.callbacks.taco_validation import (
    _extract_json,
    _normalize_keys,
    make_taco_validation_callback,
)
from src.agents.taco_gabarito.schemas import GabaritoOutput
from src.agents.taco_reviewer.schemas import TacoReviewOutput


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------

class TestExtractJson:
    def test_json_direto(self):
        text = '{"solucoes": []}'
        assert _extract_json(text) == '{"solucoes": []}'

    def test_json_em_markdown_fence(self):
        text = 'Aqui está:\n```json\n{"solucoes": []}\n```\nFim.'
        assert _extract_json(text) == '{"solucoes": []}'

    def test_json_em_fence_sem_lang(self):
        text = '```\n{"solucoes": []}\n```'
        assert _extract_json(text) == '{"solucoes": []}'

    def test_texto_antes_e_depois(self):
        text = 'Olá! {"key": "value"} Tchau!'
        assert _extract_json(text) == '{"key": "value"}'

    def test_sem_json(self):
        assert _extract_json("Nenhum JSON aqui") is None

    def test_string_vazia(self):
        assert _extract_json("") is None


# ---------------------------------------------------------------------------
# _normalize_keys
# ---------------------------------------------------------------------------

class TestNormalizeKeys:
    def test_renomeia_gabaritos_para_solucoes(self):
        raw = {"gabaritos": [{"rotulo": "x", "resumo": "y"}]}
        result = _normalize_keys(raw, "GabaritoOutput")
        assert "solucoes" in result
        assert "gabaritos" not in result

    def test_renomeia_campos_aninhados(self):
        raw = {
            "gabaritos": [
                {
                    "rotulo": "iter",
                    "resumo": "Abordagem iterativa",
                    "conceitos": ["for"],
                    "validacao": [
                        {"stdin": "1", "stdout": "1", "obtido": "1", "passed": True}
                    ],
                }
            ]
        }
        result = _normalize_keys(raw, "GabaritoOutput")
        solucao = result["solucoes"][0]
        assert "rotulo_variacao" in solucao
        assert "resumo_abordagem" in solucao
        assert "conceitos_exercitados" in solucao
        assert "validacao_exemplos" in solucao

        validacao = solucao["validacao_exemplos"][0]
        assert "esperado" in validacao
        assert "passou" in validacao

    def test_campos_corretos_nao_mudam(self):
        raw = {"solucoes": [{"rotulo_variacao": "x"}]}
        result = _normalize_keys(raw, "GabaritoOutput")
        assert result["solucoes"][0]["rotulo_variacao"] == "x"

    def test_schema_desconhecido_nao_altera(self):
        raw = {"foo": "bar"}
        result = _normalize_keys(raw, "SchemaInexistente")
        assert result == {"foo": "bar"}


# ---------------------------------------------------------------------------
# make_taco_validation_callback — GabaritoOutput
# ---------------------------------------------------------------------------

def _make_llm_response(text: str):
    """Helper: cria LlmResponse mock com texto."""
    from google.genai import types

    part = types.Part(text=text)
    content = types.Content(role="model", parts=[part])

    response = MagicMock()
    response.content = content
    return response


def _make_callback_context():
    """Helper: cria CallbackContext mock com state dict."""
    ctx = MagicMock()
    ctx.state = {}
    return ctx


class TestValidationCallbackGabarito:
    def setup_method(self):
        self.callback = make_taco_validation_callback(GabaritoOutput)

    def test_json_valido_com_campos_corretos(self):
        payload = {
            "solucoes": [
                {
                    "rotulo_variacao": "iterativa",
                    "resumo_abordagem": "Usa for.",
                    "codigo": "print(sum(map(int, input().split())))",
                    "conceitos_exercitados": ["map", "sum"],
                    "validacao_exemplos": [
                        {"stdin": "1 2", "esperado": "3", "obtido": "3", "passou": True}
                    ],
                }
            ]
        }
        ctx = _make_callback_context()
        resp = _make_llm_response(json.dumps(payload))
        result = self.callback(ctx, resp)

        assert result is not None
        assert ctx.state.get("taco_validation_ok") is True
        # Parseia o JSON de volta para verificar
        parsed = json.loads(result.content.parts[0].text)
        assert parsed["solucoes"][0]["rotulo_variacao"] == "iterativa"

    def test_json_com_campos_errados_normalizado(self):
        """Simula a resposta real que o LLM devolveu na primeira execução."""
        payload = {
            "gabaritos": [
                {
                    "rotulo": "iterativa-com-listas",
                    "resumo": "Usa for explícito.",
                    "codigo": "print(sum(map(int, input().split())))",
                    "conceitos": ["for", "split"],
                    "validacao": [
                        {"stdin": "1 2 3", "stdout": "6", "obtido": "6", "passou": True}
                    ],
                }
            ]
        }
        ctx = _make_callback_context()
        resp = _make_llm_response(json.dumps(payload, ensure_ascii=False))
        result = self.callback(ctx, resp)

        assert result is not None
        parsed = json.loads(result.content.parts[0].text)
        assert "solucoes" in parsed
        sol = parsed["solucoes"][0]
        assert sol["rotulo_variacao"] == "iterativa-com-listas"
        assert sol["resumo_abordagem"] == "Usa for explícito."
        assert sol["conceitos_exercitados"] == ["for", "split"]
        assert sol["validacao_exemplos"][0]["esperado"] == "6"

    def test_json_em_markdown_fence(self):
        payload = {"solucoes": [
            {
                "rotulo_variacao": "x",
                "resumo_abordagem": "y",
                "codigo": "pass",
                "conceitos_exercitados": [],
                "validacao_exemplos": [],
            }
        ]}
        text = f"Aqui está o resultado:\n```json\n{json.dumps(payload)}\n```"
        ctx = _make_callback_context()
        result = self.callback(ctx, _make_llm_response(text))

        assert result is not None
        assert ctx.state.get("taco_validation_ok") is True

    def test_sem_json_preserva_resposta(self):
        ctx = _make_callback_context()
        result = self.callback(ctx, _make_llm_response("Texto sem JSON nenhum"))

        assert result is None
        assert "taco_validation_error" in ctx.state

    def test_json_invalido_preserva_resposta(self):
        ctx = _make_callback_context()
        result = self.callback(ctx, _make_llm_response("{json quebrado"))

        assert result is None
        assert "taco_validation_error" in ctx.state

    def test_json_com_schema_incompativel(self):
        """JSON válido mas campos obrigatórios ausentes."""
        ctx = _make_callback_context()
        result = self.callback(ctx, _make_llm_response('{"foo": "bar"}'))

        assert result is None
        assert "Schema validation error" in ctx.state["taco_validation_error"]

    def test_resposta_sem_content(self):
        resp = MagicMock()
        resp.content = None
        ctx = _make_callback_context()
        result = self.callback(ctx, resp)
        assert result is None

    def test_resposta_sem_text_parts(self):
        from google.genai import types

        resp = MagicMock()
        resp.content = types.Content(role="model", parts=[])
        ctx = _make_callback_context()
        result = self.callback(ctx, resp)
        assert result is None


class TestValidationCallbackReviewer:
    def setup_method(self):
        self.callback = make_taco_validation_callback(TacoReviewOutput)

    def test_json_valido_reviewer(self):
        payload = {
            "pontos_fortes": ["Código funciona"],
            "problemas_encontrados": [
                {
                    "tipo": "estilo",
                    "gravidade": "baixa",
                    "descricao": "range(len()) desnecessário",
                    "linha_aproximada": 4,
                }
            ],
            "sugestoes_de_melhoria": ["Pesquise iteração direta."],
            "avaliacao_geral": {
                "corretude": 100,
                "estilo": 70,
                "eficiencia": 80,
            },
        }
        ctx = _make_callback_context()
        result = self.callback(ctx, _make_llm_response(json.dumps(payload)))

        assert result is not None
        parsed = json.loads(result.content.parts[0].text)
        assert parsed["avaliacao_geral"]["corretude"] == 100
        assert len(parsed["problemas_encontrados"]) == 1
