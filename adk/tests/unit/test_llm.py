"""Testes unitários para shared.llm — fábrica de modelo com fallback."""

import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# ---------------------------------------------------------------------------
# test_git_tools.py corrompe pydantic.BaseModel = object no nível de módulo,
# o que quebra o import real de litellm (que depende do BaseModel verdadeiro).
# Para isolar este módulo, criamos stubs leves de litellm e google.adk antes
# de importar shared.llm.
# ---------------------------------------------------------------------------


class _FakeRouter:
    """Stub do litellm.Router para testes sem dependência do pacote real."""

    def __init__(self, **kwargs):
        self.model_list = kwargs.get("model_list", [])
        self.fallbacks = kwargs.get("fallbacks")
        self.num_retries = kwargs.get("num_retries", 2)
        self.timeout = kwargs.get("timeout", 120)

    async def acompletion(self, *args, **kwargs):
        ...

    def completion(self, *args, **kwargs):
        ...


class _FakeLiteLlm:
    def __init__(self, model: str = "", **kwargs):
        self.model = model


# Stub litellm (evita import real que precisa de pydantic íntegro)
_litellm_stub = sys.modules.get("litellm")
if _litellm_stub is None or not hasattr(_litellm_stub, "__file__"):
    _litellm_stub = types.ModuleType("litellm")
    _litellm_stub.Router = _FakeRouter  # type: ignore[attr-defined]
    _litellm_stub.acompletion = None  # type: ignore[attr-defined]
    _litellm_stub.completion = None  # type: ignore[attr-defined]
    _litellm_stub.drop_params = False  # type: ignore[attr-defined]
    sys.modules["litellm"] = _litellm_stub

# Stub google.adk.models.lite_llm
_adk_model_stub = types.ModuleType("google.adk.models.lite_llm")
_adk_model_stub.LiteLlm = _FakeLiteLlm  # type: ignore[attr-defined]

for _mod_name, _mod_obj in [
    ("google", types.ModuleType("google")),
    ("google.adk", types.ModuleType("google.adk")),
    ("google.adk.models", types.ModuleType("google.adk.models")),
    ("google.adk.models.lite_llm", _adk_model_stub),
]:
    sys.modules.setdefault(_mod_name, _mod_obj)

import shared.llm as llm_mod  # noqa: E402


@pytest.fixture()
def config_yaml(tmp_path) -> Path:
    cfg = {
        "model_list": [
            {
                "model_name": "openai/gpt-4",
                "litellm_params": {"model": "openai/gpt-4", "api_key": "fake-key"},
            },
            {
                "model_name": "groq/llama-3.3-70b-versatile",
                "litellm_params": {"model": "groq/llama-3.3-70b-versatile", "api_key": "fake-key"},
            },
        ],
        "router_settings": {
            "num_retries": 1,
            "timeout": 30,
            "fallbacks": [{"openai/gpt-4": ["groq/llama-3.3-70b-versatile"]}],
        },
    }
    path = tmp_path / "llm_config.yaml"
    path.write_text(yaml.dump(cfg))
    return path


@pytest.fixture(autouse=True)
def _reset_router():
    """Restaura estado do módulo entre testes."""
    original_acompletion = _litellm_stub.acompletion
    original_completion = _litellm_stub.completion
    yield
    llm_mod._router = None
    _litellm_stub.acompletion = original_acompletion
    _litellm_stub.completion = original_completion


class TestLoadConfig:
    def test_returns_empty_when_file_missing(self):
        with patch.object(llm_mod, "_CONFIG_PATH", Path("/nonexistent/llm_config.yaml")):
            cfg = llm_mod._load_config()
        assert cfg == {}

    def test_returns_dict_when_file_exists(self, config_yaml):
        with patch.object(llm_mod, "_CONFIG_PATH", config_yaml):
            cfg = llm_mod._load_config()
        assert "model_list" in cfg
        assert len(cfg["model_list"]) == 2


class TestBuildRouter:
    def test_returns_none_without_model_list(self):
        assert llm_mod._build_router({}) is None

    def test_returns_router_with_valid_config(self, config_yaml):
        cfg = yaml.safe_load(config_yaml.read_text())
        router = llm_mod._build_router(cfg)
        assert router is not None
        assert len(router.model_list) == 2


class TestGetModel:
    def test_returns_litellm_instance(self, monkeypatch):
        monkeypatch.delenv("ADK_LLM_MODEL", raising=False)
        model = llm_mod.get_model()
        assert isinstance(model, _FakeLiteLlm)
        assert model.model == "github_copilot/gpt-4"

    def test_respects_env_override(self, monkeypatch):
        monkeypatch.setenv("ADK_LLM_MODEL", "custom/model-x")
        model = llm_mod.get_model()
        assert model.model == "custom/model-x"


class TestInit:
    def test_patches_litellm_when_config_present(self, config_yaml):
        with patch.object(llm_mod, "_CONFIG_PATH", config_yaml):
            llm_mod._init()

        router = llm_mod.get_router()
        assert router is not None
        assert _litellm_stub.acompletion == router.acompletion
        assert _litellm_stub.completion == router.completion

    def test_no_patch_when_no_config(self):
        original = _litellm_stub.acompletion

        with patch.object(llm_mod, "_CONFIG_PATH", Path("/nonexistent/llm_config.yaml")):
            llm_mod._init()

        assert llm_mod.get_router() is None
        assert _litellm_stub.acompletion is original
