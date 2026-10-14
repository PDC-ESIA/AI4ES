"""Os `test_config.json` da suíte de avaliação apontam para métricas que existem.

Cada `test_config.json` de `tests/eval/evalsets/` liga uma métrica própria à sua função
por texto, em `custom_metrics.<métrica>.code_config.name`, e o ADK só importa esse
caminho quando a rodada começa. Como a suíte de avaliação é opt-in e usa LLM, renomear
ou mover uma função de `tests/eval/metrics.py` só apareceria na próxima rodada. Aqui a
mesma resolução roda sem LLM.
"""

import importlib
import json
from pathlib import Path

import pytest

from tests.eval import metrics

_EVALSETS = Path(__file__).resolve().parents[1] / "eval" / "evalsets"
_CONFIGS = sorted(_EVALSETS.glob("*/test_config.json"))
_PREFIXO = "ai4es_"


def _resolver(caminho: str):
    """Mesma resolução de `_get_metric_function`, no `custom_metric_evaluator` do ADK."""
    modulo, funcao = caminho.rsplit(".", 1)
    return getattr(importlib.import_module(modulo), funcao)


def test_ha_test_configs_para_conferir():
    assert _CONFIGS, f"nenhum test_config.json em {_EVALSETS}"


@pytest.mark.parametrize("config", _CONFIGS, ids=lambda caminho: caminho.parent.name)
def test_metricas_proprias_do_test_config_resolvem(config):
    dados = json.loads(config.read_text(encoding="utf-8"))
    nos_criterios = {
        nome for nome in dados.get("criteria", {}) if nome.startswith(_PREFIXO)
    }
    ligadas = dados.get("custom_metrics", {})

    # Métrica própria sem `custom_metrics` chega ao ADK sem caminho e quebra na rodada;
    # `custom_metrics` sem critério nunca é avaliada.
    assert nos_criterios == set(ligadas)

    for nome, ligacao in ligadas.items():
        assert nome in metrics.DESCRICOES, f"{nome} não é registrada por metrics.py"
        caminho = ligacao["code_config"]["name"]
        assert callable(_resolver(caminho)), caminho
